# Architecture decision records

An architecture decision record (ADR) captures one significant design decision: the situation, the choice, the options turned down and what the choice costs. ADR-001 to ADR-008 come from Appendix F of the approved proposal and were recorded in Sprint 0 (story US-14). Later ones are recorded when a sprint makes a new decision.

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](ADR-001-independent-gateway.md) | Independent gateway between the agent and protected tools | Accepted |
| [ADR-002](ADR-002-opa-rego-policy.md) | OPA and Rego for deterministic policy | Accepted |
| [ADR-003](ADR-003-ml-risk-advisory.md) | Machine learning risk is advisory to hard policy | Accepted |
| [ADR-004](ADR-004-rag-explains-after-decision.md) | RAG explains after the decision | Accepted |
| [ADR-005](ADR-005-postgresql-pgvector.md) | PostgreSQL with pgvector | Accepted |
| [ADR-006](ADR-006-dual-deployment-profile.md) | Dual deployment profile | Accepted |
| [ADR-007](ADR-007-external-llm-adapter.md) | External LLM through a provider-neutral adapter | Accepted |
| [ADR-008](ADR-008-synthetic-data-only.md) | Synthetic banking data only | Accepted |
| ADR-009 | Public hosting platform: Railway or Render | Planned for Sprint 3 (US-11a) |
| [ADR-010](ADR-010-shared-contracts-and-execution-tokens.md) | Shared contracts and HMAC-signed single-use execution tokens | Accepted |
| [ADR-011](ADR-011-demo-bank-in-memory.md) | The demo bank keeps its data in memory | Accepted |
| [ADR-012](ADR-012-gateway-decision-pipeline.md) | Gateway decision pipeline, caller identity and idempotent outcomes | Accepted |
| [ADR-013](ADR-013-ownership-lookup.md) | The gateway checks record ownership with the bank | Accepted |

## When to write a new ADR

Write one when a change affects a security boundary, persistence, an external service or deployment. This is the rule in the proposal's change control section and in the working agreement.

1. Copy `template.md` to `ADR-0NN-short-title.md` with the next number.
2. Fill it in and set the status to Proposed.
3. Open a pull request. Once a Code Owner and the Product Owner approve, set the status to Accepted and add a row to the table above.
4. Never rewrite an accepted ADR. If a decision changes, write a new ADR and mark the old one as Superseded by the new number.
