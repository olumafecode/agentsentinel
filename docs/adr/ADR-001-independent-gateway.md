# ADR-001: Independent gateway between the agent and protected tools

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-10 (recorded in Sprint 0; decision taken in the approved proposal, Appendix F) |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-01, FR-02, FR-08, FR-09; NFR-01, NFR-02, NFR-03 |
| Stories | US-18, US-23, US-29 |

## Context

An AI agent can be mistaken, manipulated by content it reads, or compromised. Instructions in a prompt are guidance, not enforcement: a confused or hijacked agent can ignore them. If the agent holds bank credentials, nothing outside the model stands between a bad decision and a real side effect.

FR-01 and FR-09 require every protected call to be intercepted and blocked calls to never reach the bank API. That needs one path to the tools that the agent cannot go around.

## Decision

- All protected tool calls go through the Sentinel Gateway, which acts as the Policy Enforcement Point. Vera proposes actions; the gateway decides and enforces.
- Vera holds the gateway address only. It never receives a bank API address or credential.
- For an allowed action the gateway issues a signed, single-use execution token. The demo bank API accepts a protected request only with a valid token. In the Kubernetes profile, NetworkPolicy also blocks any direct network path from the agent to the bank API.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| Guardrails in the agent's prompt or framework | Rejected. They live inside the thing being controlled and cannot be enforced. |
| A checking library inside the agent process | Rejected. Same trust boundary as the agent, so a compromised agent can skip it. |
| Checks inside each bank API | Rejected. Rules would be duplicated across tools, with no single place to audit decisions. |

## Consequences

What we gain:

- One enforceable choke point for every protected action.
- Security logic is tested and versioned separately from the agent's reasoning.
- One place produces the audit trail and the decision record.

What it costs:

- Every action takes an extra network hop, which counts against the 300 ms latency budget (NFR-02).
- The gateway becomes a critical dependency. It needs replicas, health probes and fail-closed behavior.
- Non-bypassability has to be proven, not assumed (US-29).
