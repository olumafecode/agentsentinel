# ADR-004: RAG explains after the decision

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-10 (recorded in Sprint 0; decision taken in the approved proposal, Appendix F) |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-12, FR-13; NFR-02, NFR-07 |
| Stories | US-06a, US-26 |

## Context

Auditors and approvers need to know why an action was blocked or held, in plain English and tied to bank policy (FR-12). A language model is good at writing that explanation, but it can state things that are not true, and it must not decide its own authority.

## Decision

- The explanation service runs after the gateway has made and enforced the decision. It retrieves passages from the synthetic bank policy documents, writes a plain-English explanation and returns the policy section IDs it relied on.
- Cited IDs are checked against the retrieved passages. An explanation with a citation that was not retrieved is rejected and a safe fallback is shown.
- The explanation is stored as evidence and can never change the outcome. If the LLM is unavailable, the decision is unaffected.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| The LLM both decides and explains | Rejected. The model would be judging its own permission, and a hallucination could become an allowed action. |
| Fixed template explanations with no retrieval | Kept only as the fallback. Simple and safe, but not grounded in the policy text that auditors want to see. |

## Consequences

What we gain:

- Reviewers get readable, cited evidence.
- The decision path stays fast and deterministic; the explanation may take up to 3 seconds in the background (NFR-02).
- LLM failure degrades the explanation only, never security.

What it costs:

- An explanation can arrive after the decision is shown.
- It adds an external LLM dependency and cost.
- Citation checking reduces but does not remove the risk of a misleading explanation; a sample is reviewed by hand (NFR-07).
