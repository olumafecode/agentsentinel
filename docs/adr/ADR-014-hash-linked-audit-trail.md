# ADR-014: The hash-linked audit trail in PostgreSQL

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-18 |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-13, FR-14; NFR-03, NFR-06, NFR-11 |
| Stories | US-19 (US-19.1 to US-19.5), US-20, and later US-06b, US-26 |

## Context

FR-13 asks for an audit event for every evaluated action, and NFR-06 for a complete record of every action. An auditor must also be able to trust the record: an event changed or removed after the fact has to be detectable. ADR-005 puts the audit trail in PostgreSQL with a gateway role that can insert but not change rows, and `data/synthetic/README.md` fixes the hash rule. This ADR settles how the chain is built and checked.

## Decision

- **Storage.** Schema `audit` holds `events` (the AuditEvent entity) and `tool_calls` (the ToolCall entity). Numbered SQL migrations, run by `python -m sentinel_audit migrate` in one transaction, create them. In Docker Compose a one-shot `audit` container runs the migrations before the gateway starts.
- **Chain.** Each event takes the next position (`EVT-000001`, `EVT-000002` and so on) and the hash of the event before it. An append takes a transaction-level advisory lock, reads the last event and inserts the new one, so concurrent writers cannot fork the chain.
- **Append-only.** The gateway connects as `sentinel_gateway`, which has only `SELECT` and `INSERT` on the two tables. A trigger also refuses `UPDATE`, `DELETE` and `TRUNCATE` for every role, the owner included.
- **Checks.** `verify-chain` recomputes every hash and link and names each broken event. `completeness` checks that every correlation ID has `action_received`, one `decision_made` with reasons, and the one final event that fits the decision. Both exit with 1 on a problem, so CI can run them.
- **Gateway.** With `AUDIT_DATABASE_URL` set, the gateway writes through this store. Its readiness probe reports not ready while the database is unreachable, and it refuses actions it cannot audit (ADR-012).

## Alternatives considered

| Alternative | Outcome |
|---|---|
| A separate audit service with its own HTTP API | Deferred to US-06b, which adds the timeline API. For writing, a network hop adds latency to every decision and one more service that can fail, while the database role already gives the append-only guarantee. |
| Compute the hash inside PostgreSQL | Rejected. The documented hash rule is defined over Python-style JSON, and matching it in SQL is fragile. The `verify-chain` command is the authority either way. |
| Sequence numbers from a PostgreSQL sequence | Rejected. A rolled-back insert leaves a gap, which would look like a deleted event. Positions come from the last event under the lock instead. |
| Rely only on the trigger, or only on grants | Rejected. Grants stop the gateway; the trigger also stops accidents by the owner. Neither stops a determined owner, which is why the chain exists. |

## Consequences

What we gain:

- Every evaluated action has a stored, ordered, tamper-evident record (FR-13, NFR-06), checked in CI on every pull request.
- A changed or deleted event is reported by event ID.
- The same completeness check serves US-19 now and the scenario evaluation in US-26 later.

What it costs:

- Appends are serialized. That is a single short transaction per event and fine at demo load; US-27 measures it.
- Event IDs have six digits, so one chain holds at most 999,999 events, enough for this project. A longer-lived system would widen the format in the schema first.
- Removing events from the end of the chain leaves the rest still linked. The database refuses deletes, and publishing the latest hash outside the database (for example in each sprint's evidence) would close the gap if needed.
- A payload string containing a NUL character cannot be stored in `jsonb`, so such an action is refused with HTTP 503 rather than run unaudited.
