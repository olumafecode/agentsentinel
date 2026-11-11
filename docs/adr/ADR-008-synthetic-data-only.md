# ADR-008: Synthetic banking data only

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-10 (recorded in Sprint 0; decision taken in the approved proposal, Appendix F) |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | NFR-08, NFR-14 |
| Stories | US-15, US-16, US-21 |

## Context

Real banking data cannot be used in a student project: it is not available, and using it would create privacy and compliance risk. The project still needs realistic customers, accounts, transactions and agent actions, including adversarial cases, and they must be reproducible.

## Decision

- All data is invented by seeded generators that follow the rules in `data/synthetic/README.md`: reserved email domains, the fictional phone range, the project's own identifier formats, and no government IDs, card numbers or credentials.
- Labels for the risk model come from the written rules in `data/synthetic/labelling-rules.md`. The test split is frozen before tuning.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| Anonymized real data | Rejected. Not available, and re-identification risk remains. |
| A public banking dataset | Rejected. Licence and privacy questions aside, public datasets do not contain agent tool calls or prompt-injection sequences. |

## Consequences

What we gain:

- No privacy or compliance exposure, including when prompts go to an external LLM.
- Fully reproducible: the same seed gives the same data.
- Adversarial cases can be designed to cover every failure mode and use case.

What it costs:

- Synthetic behavior is simpler than real traffic, so model metrics will not transfer directly to a real bank. The final report says so.
- The labels come from rules the team wrote, so a model could score well by learning those rules. Held-out scenarios and the external AgentDojo benchmark offset that.
