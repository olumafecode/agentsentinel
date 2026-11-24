# ADR-015: How the gateway asks OPA, and what it records

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-23 |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-03, FR-04, FR-06, FR-08, FR-13, FR-17; NFR-01, NFR-03 |
| Stories | US-02a (US-02a.1 to US-02a.5), and later US-02b, US-03, US-21 |

## Context

ADR-002 chose OPA and Rego for the bank's deterministic rules and asked that every decision record the policy version and the rules that matched, and that high-impact actions fail closed when OPA cannot be reached (AT-12). In Sprint 1 the gateway enforced the tool rules itself: a `ToolAllowlistCheck` read the agent's `allowed_tools` and each tool's `allowed_task_types` from its own JSON files. US-02a moves those rules, the ban on bulk export and the refund amount rules into OPA. This ADR settles how the gateway asks, where each piece of policy data lives, where the version comes from and how the gateway is tested without OPA.

On 23 November 2026 the Product Owner confirmed the tools each task allows, with three changes from Sprint 1: a refund is issued only in a refund request, not in a dispute; Vera may call `get_accounts`; and Vera may call `freeze_account` while handling a dispute, so that she can stop further debits as soon as a customer reports a suspected fraud.

## Decision

- **One question per action.** A `PolicyCheck` in the HARD_RULE stage, before the customer scope check, posts the agent, the tool and the action to OPA's data API at `/v1/data/agentsentinel/gateway/decision`. The answer is a list of violations, each with a rule name, a decision (BLOCK or HUMAN_REVIEW), a reason code and a message. No violations means no objection; the policy never allows an action on its own.
- **Combining the answer.** The check asks for the strongest decision among the violations, keeps every reason code in a fixed order (`POLICY_DENY` before `TOOL_NOT_ALLOWED` before `INVALID_ARGUMENTS` before `REFUND_OVER_LIMIT`) and uses the leading rule's message as the summary.
- **Where the policy data lives.** The task-to-tool table, the bulk export list and the refund settings are in `policies/opa/agentsentinel/data.json`, the one place both the live policy and the dataset generator (US-21) read them. The agent's own allowlist stays in the gateway's agent registry, because it belongs to the agent and can change with its status; the gateway sends it with each action.
- **The version.** OPA serves `policies/opa` as a bundle. The gateway asks with `?provenance=true` and takes the bundle's `revision` from `.manifest` as the `policy_version`. A rule change raises the revision. The version is recorded on every decision the policy took part in, ALLOW included, and the matched rules go into the `decision_made` event's check details.
- **Failing closed.** An answer the gateway cannot trust counts as no answer: OPA unreachable or slow (2-second timeout by default), any status but 200, a policy that is not loaded, no bundle revision, or a violation with an unknown decision or reason code. The check then raises `PolicyUnavailable`, which the orchestrator turns into BLOCK with `DEPENDENCY_UNAVAILABLE` and logs. This holds for every action, not only high-impact ones, because without the policy no action has been judged. The gateway's readiness probe reports not ready while OPA is down.
- **Changes to ADR-012.** Two rows of ADR-012's stage table change. In the HARD_RULE stage the bank policy now runs before the customer scope check, so a tool the policy refuses never causes an ownership lookup at the bank. And the rule for refunds above the automatic limit is part of the policy, so it asks for HUMAN_REVIEW from the HARD_RULE stage; US-03 adds the approval workflow, not a separate MANDATORY_REVIEW check for the limit.
- **Testing.** The Rego rules have unit tests with 100% coverage, run with `opa test` in CI. The gateway's own unit tests use a stand-in policy that never objects. Tests of the real policy through the gateway, and the acceptance tests, start a real OPA server with the bundle; CI installs the same OPA version as the image and fails if it is missing.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| Keep the tool allowlist in the gateway and use OPA only for new rules | Rejected. Two places would decide which tools are allowed, and the dataset labels would follow neither for certain. |
| Put the agents' allowlists in the OPA data as well | Rejected for now. The agent registry already holds them with the agent's status, which quarantine changes at runtime (US-05). Sending them as input keeps one source. |
| Let OPA return a single decision instead of a list of violations | Rejected. The audit trail needs every rule that matched, and the gateway already combines findings by precedence. |
| A policy version written in the Rego or the data | Rejected. It could fall out of step with the bundle; the bundle revision is what OPA itself reports. |
| Evaluate Rego inside the gateway's process | Rejected. There is no maintained Rego engine for Python, and a separate OPA keeps policy releases independent of gateway releases (ADR-002). |
| Fail open for read-only tools when OPA is down | Rejected. A read can leak another customer's data as surely as a write can change it (AT-02). |

## Consequences

What we gain:

- The rules are Rego, reviewed in pull requests, versioned, and tested at their boundaries.
- Every audited decision shows the policy bundle version and the rules that matched.
- The live policy and the dataset labels read the same settings, and a test fails if `labelling-rules.md` disagrees with them.

What it costs:

- One more network call on every action that passes the context checks.
- The gateway cannot decide anything while OPA is down; the stack waits for OPA's health check before starting the gateway.
- Running the policy and acceptance tests on a developer's machine needs the `opa` command; without it they are skipped.
- Until the approval service arrives in US-03, a refund above the automatic limit is blocked rather than held for a person.
