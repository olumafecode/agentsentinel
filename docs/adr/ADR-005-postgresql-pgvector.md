# ADR-005: PostgreSQL with pgvector

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-10 (recorded in Sprint 0; decision taken in the approved proposal, Appendix F) |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-12, FR-13, FR-14; NFR-06, NFR-13 |
| Stories | US-19, US-06a, US-27 |

## Context

The system needs transactional storage for bank data, approvals and the audit trail, and a small vector index for policy passages. Every extra datastore is another thing to deploy, secure, back up and restore inside a short project.

## Decision

- One PostgreSQL instance holds transactional data, the hash-linked audit trail, approvals, incidents and the policy embeddings (through the pgvector extension).
- Services use separate schemas and database roles. The gateway's role can insert audit rows but not update or delete them.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| A separate vector database | Rejected for this release. It adds a service to run for a few policy documents' worth of embeddings. |
| SQLite | Rejected. It does not suit several services writing at once and has no pgvector. |
| A document or key-value store | Rejected. The data is relational and the audit trail benefits from database constraints and roles. |

## Consequences

What we gain:

- One datastore to deploy, back up and restore (NFR-13).
- Database roles and constraints support the append-only audit trail (NFR-06).
- The same engine is available on Railway, Render and Kubernetes.

What it costs:

- Vector search is suitable only at small scale, which is all this project needs.
- One database is a single point of failure in the demo.
- A shared database can couple services; separate schemas and the repository pattern limit that.
