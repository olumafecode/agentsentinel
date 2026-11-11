# ADR-003: Machine learning risk is advisory to hard policy

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-10 (recorded in Sprint 0; decision taken in the approved proposal, Appendix F) |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-07, FR-08, FR-18; NFR-03 |
| Stories | US-04, US-21, US-25 |

## Context

Rules catch what can be written down in advance. They miss sequences where each action looks valid, such as many small refunds. A machine learning model can score those, but models make mistakes and are hard to audit.

The proposal's target is that 100% of explicitly denied policy cases are blocked. That cannot depend on a model.

## Decision

- Decisions follow a fixed precedence: hard deny, then quarantine condition, then mandatory human review, then risk-based escalation, then allow.
- The risk score can only add caution. A high score can raise an allow to human review or block according to configured thresholds. A low score can never allow an action that a hard rule denies.
- Thresholds are tuned on validation data only and are recorded with the model version.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| The model makes the final decision | Rejected. A false negative would allow a forbidden action, and the decision would be hard to explain or reproduce. |
| No model, rules only | Rejected. It leaves the valid-but-unintended sequence failure mode (UC-06) uncovered. Rules-only is kept as evaluation Setup B for comparison. |

## Consequences

What we gain:

- Deterministic enforcement is predictable and fully testable.
- The model adds coverage exactly where rules are weak.
- The value added by the model can be measured by comparing Setup B with Setup C.

What it costs:

- Model escalations can block or delay legitimate actions; the false-block target is under 5%.
- The model's benefit is limited to what the rules do not already cover.
- Two decision sources must be explained to reviewers; the audit event records both.
