# ADR-002: OPA and Rego for deterministic policy

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-10 (recorded in Sprint 0; decision taken in the approved proposal, Appendix F) |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-03, FR-04, FR-06, FR-17; NFR-01, NFR-09 |
| Stories | US-02a, US-02b, US-07 |

## Context

Bank rules such as tool permissions per task, refund limits and the ban on bulk export must be reviewable by people who do not read application code, versioned on their own, and unit-tested. FR-06 calls for deterministic policy evaluation and FR-17 for versioned policy bundles.

## Decision

- Open Policy Agent (OPA) is the Policy Decision Point. Rules are written in Rego under `policies/opa`, tested with `opa test` in CI and released as versioned bundles.
- The gateway asks OPA for a decision on every action and records the policy version and matched rules in the audit event.
- If OPA cannot be reached, high-impact actions fail closed (AT-12).

## Alternatives considered

| Alternative | Outcome |
|---|---|
| Rules hard-coded in the gateway's Python | Rejected. Quick to start, but policy would be mixed with application code and could not be versioned or simulated independently. |
| Another policy engine such as Cedar | Workable. OPA was chosen for its maturity, test tooling and wide use with Kubernetes. |
| Rules written into the LLM prompt | Rejected. A prompt is not an enforcement mechanism. |

## Consequences

What we gain:

- Policy is code: reviewed in pull requests, unit-tested and versioned.
- The same engine supports policy simulation against stored events (UC-10).
- Policy changes do not require a gateway release.

What it costs:

- The team has to learn Rego.
- One more network call per decision, so it needs a timeout and a fail-closed rule.
- Policy data, such as thresholds and the agent registry, must be kept in step with the database.
