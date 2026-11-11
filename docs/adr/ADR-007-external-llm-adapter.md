# ADR-007: External LLM through a provider-neutral adapter

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-10 (recorded in Sprint 0; decision taken in the approved proposal, Appendix F) |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-01, FR-12; NFR-08, NFR-14 |
| Stories | US-17, US-24, US-06a |

## Context

Vera's live mode and the explanation service need a large language model. Hosting one in the cluster would need GPU or large memory, adding cost and deployment risk without improving what the capstone contributes.

## Decision

- All LLM access goes through one adapter interface, with at least one provider implementation and a mock.
- Model name, version and settings are pinned and recorded with evaluation runs.
- No LLM is hosted in the cluster. Policy enforcement, risk scoring, persistence, audit and orchestration stay inside the project.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| Self-host an open model in the cluster | Rejected. Cost and operational risk for no gain in the project's core contribution. |
| Call a provider's SDK directly from each service | Rejected. It locks the code to one provider and makes offline testing hard. |

## Consequences

What we gain:

- Low cost, and the provider can be replaced.
- The mock allows tests and demos to run without network access; scripted mode keeps the final demo deterministic.
- Only one module handles provider keys.

What it costs:

- An external dependency with rate limits and per-call cost; a spend cap is set.
- Prompts leave the system, which is acceptable only because all data is synthetic (ADR-008).
- Provider model updates can change behavior; versions are pinned and scenarios are re-run when they change.
