# ADR-012: Gateway decision pipeline, caller identity and idempotent outcomes

| | |
|---|---|
| Status | Accepted; the HARD_RULE order and the refund limit rule are amended by [ADR-015](ADR-015-bank-policy-in-opa.md) |
| Date | 2026-11-18 |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-01, FR-02, FR-08, FR-09, FR-13; NFR-01, NFR-02, NFR-03, NFR-06 |
| Stories | US-18 (US-18.2 to US-18.6), and later US-01, US-02a, US-02b, US-03, US-04, US-05, US-19 |

## Context

ADR-001 puts the Sentinel Gateway between Vera and every bank tool, and ADR-010 gives it a signed single-use token to prove an action was allowed. Building the evaluate endpoint (US-18) needed four more decisions.

1. **Who is asking.** A request body can say anything. If the gateway believed the agent ID, session and customer in the body, a manipulated agent could claim another customer's session and every later check would be judging a lie (FR-02, UC-04).
2. **How rules combine.** Sprint 1 has only context checks, but by Sprint 3 there are OPA rules, provenance checks, mandatory review, quarantine and a risk score. They need one place to run and one fixed order of precedence (Appendix E, FR-08), and adding a rule should not mean reworking the gateway.
3. **What happens when something breaks.** A policy engine that times out, a bug in a rule or an audit trail that cannot be written must never let an action through (NFR-01).
4. **Retries.** An agent that times out will retry. A retried refund must not pay twice, and the same correlation ID must get the same answer (NFR-03).

## Decision

**Caller identity.** Each agent has its own API key, sent as `Authorization: Bearer <key>` and held by the gateway only as a SHA-256 hash (`AGENT_KEYS`). The gateway works out the agent's ID from the key. A request without a valid key gets HTTP 401 and is not evaluated, because nothing can be attributed to it.

**Customer session.** When a customer signs in, Veridane's identity service issues a session token naming the session, customer, agent, task and channel. Vera passes it in `X-Session-Token`. It is signed like an execution token but with its own key (`SESSION_TOKEN_KEY`) and prefix (`s1`), lasts 30 minutes by default and at most 4 hours, and can be used for many actions. Vera never holds the key. In the demo, `python -m sentinel_gateway issue-session` stands in for the identity service.

**Pipeline.** Every check belongs to one stage, and stages run in this order:

| Stage | Holds | Arrives in |
|---|---|---|
| CONTEXT | Context binding, agent status, request freshness, known tool | US-18 |
| HARD_RULE | Customer scope, tool allowlist, then OPA policy and provenance | US-01, US-02a, US-02b |
| CONTAINMENT | Quarantine after repeated violations | US-05 |
| MANDATORY_REVIEW | Refunds above the automatic limit | US-03 |
| RISK | The machine learning score | US-04 |

A check either has no objection or asks for HUMAN_REVIEW, BLOCK or QUARANTINE with reason codes and a summary. No check can allow an action: ALLOW is what remains when every check ran and none objected.

**Precedence.** The strongest decision wins: QUARANTINE, then BLOCK, then HUMAN_REVIEW, then ALLOW. QUARANTINE outranks BLOCK, as the Product Owner confirmed in Sprint 0. Reasons from the winning decision come first. If a CONTEXT check objects, no later stage runs. Once any check asks for BLOCK or QUARANTINE, the review and risk stages are skipped, since neither can overturn a hard stop (ADR-003).

**Fail closed.**

- A check that raises an error counts as BLOCK with `DEPENDENCY_UNAVAILABLE`.
- A request that fails validation is still decided: it is blocked with `MISSING_CONTEXT`, `UNKNOWN_TOOL` or `INVALID_ARGUMENTS`. One without a valid correlation ID is given a new ID first, so it is audited like any other.
- HUMAN_REVIEW with no approval service to hold the action becomes BLOCK with `DEPENDENCY_UNAVAILABLE`.
- If `action_received` or `decision_made` cannot be written to the audit trail, the gateway returns HTTP 503 and runs nothing.
- Requests stamped more than 5 minutes ago, or more than 30 seconds ahead, are blocked as `STALE_REQUEST`.

**Idempotency.** The gateway keeps each outcome under its correlation ID together with a fingerprint of the caller, the session token and the exact body. A repeat with the same fingerprint gets the stored outcome, marked `X-Idempotent-Replay: true`, and nothing runs again. The same ID with a different fingerprint gets HTTP 409. Identical requests that arrive together are handled one after the other. Outcomes are kept for an hour, which is longer than the 5-minute freshness window, so an expired record can never be repeated.

**Forwarding.** For ALLOW the gateway signs an execution token and calls the bank itself, sending the canonical JSON the token's argument hash was computed from. Whatever the bank answers, including a timeout, is stored as the execution result, so a retry cannot cause a second call.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| Trust the agent ID and customer in the request body | Rejected. It is the exact weakness FR-02 exists to close. |
| OAuth 2.0 client credentials and JWTs from an identity provider | Stronger and standard, but needs an identity provider in the stack. Deferred: the bearer key and the session token can be replaced by one later without changing the checks, which only see the bound context. |
| Mutual TLS between Vera and the gateway | Proves which service connects but not which customer session the action belongs to. Can be added in the Kubernetes profile (US-23) as a second layer. |
| Return HTTP 422 for malformed requests, as FastAPI does by default | Rejected. A malformed action is often the interesting one. Deciding and auditing it keeps NFR-06 at 100%. |
| Put every rule in OPA from the start | Rejected for context checks. They need the verified session and the registry, they are cheap, and keeping them in the gateway means OPA being down cannot hide a forged session. OPA arrives as a HARD_RULE check in US-02a. |
| Use a client-supplied `Idempotency-Key` header | Rejected. The correlation ID already identifies the action across every service and the audit trail; a second identifier would only drift from it. |

## Consequences

What we gain:

- An agent cannot act under another agent's ID, for another customer's session or for a task the customer did not ask for.
- New rules are added as small classes in the right stage, without changing the orchestrator or the endpoint.
- Every JSON action that reaches the gateway with a valid agent key has a decision and an audit trail, even when its fields are wrong or missing.
- A retried refund pays once.

What it costs:

- Two more secrets to manage: `SESSION_TOKEN_KEY` and one key per agent.
- The outcome record is in memory and per process, like the bank's replay guard. Before the gateway runs more than one replica (US-23), the record moves to PostgreSQL. A gateway restart forgets it, so a request repeated within 5 minutes of a restart could be evaluated again. The bank's replay guard still stops the old token.
- Vera receives the execution token in an ALLOW decision because the contract requires it. Normally the gateway has already used it, so a replay fails (tested). If the bank could not be reached, the token still allows that one call, unchanged, for up to 60 seconds. It must be kept out of logs.
- Until US-01 adds the customer scope and tool allowlist checks, any registered tool is allowed within a valid session.
