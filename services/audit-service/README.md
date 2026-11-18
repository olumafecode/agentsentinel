# Audit and incident service

Stores the hash-linked audit trail in PostgreSQL and checks it. The gateway writes to it for every action; the `verify-chain` and `completeness` commands prove the trail is intact and whole. Incident timelines by correlation ID follow in Sprint 3 (US-06b).

| | |
|---|---|
| First built in | Sprint 1, extended in Sprint 3 |
| Stories | US-19 (tasks US-19.1 to US-19.5); later US-06b |
| Requirements | FR-13, FR-14; NFR-06, NFR-11 |
| Decision records | [ADR-005](../../docs/adr/ADR-005-postgresql-pgvector.md), [ADR-014](../../docs/adr/ADR-014-hash-linked-audit-trail.md) |

## What is stored

Schema `audit` in the shared PostgreSQL database:

| Table | Holds |
|---|---|
| `audit.events` | Every audit event, in the shape of the AuditEvent entity in `data/synthetic/models.py`, with `previous_event_hash` and `event_hash` |
| `audit.tool_calls` | Every well-formed action Vera proposed, one row per correlation ID (the ToolCall entity) |
| `audit.schema_migrations` | Which migrations have run |

Each event's hash follows the audit hash rule in `data/synthetic/README.md`: SHA-256 of every field except `event_hash`, as JSON with sorted keys and no spaces. The first event points at 64 zeros. Writers take a lock for each append, so the chain stays one unbroken line even with several gateway threads or replicas.

## Append-only

- The gateway connects as `sentinel_gateway`, a role that can insert and read audit rows and nothing else. Updates, deletes, truncation and schema changes are refused with "permission denied".
- A trigger refuses updates, deletes and truncation for every role, the table owner included.
- Someone who owns the tables can still switch the trigger off and edit a row. `verify-chain` then reports the exact event that was changed.

## Commands

```
python -m sentinel_audit migrate        # create or update the schema and the gateway's role
python -m sentinel_audit verify-chain   # check every link; exit code 1 if the chain is broken
python -m sentinel_audit completeness   # check every action has received, decided and final events
```

| Variable | Used by | Meaning |
|---|---|---|
| `AUDIT_ADMIN_DATABASE_URL` | `migrate` | An account that owns the schema, for example the PostgreSQL superuser |
| `AUDIT_GATEWAY_DB_PASSWORD` | `migrate` | Password for `sentinel_gateway`, at least 16 characters |
| `AUDIT_DATABASE_URL` | `verify-chain`, `completeness`, and the gateway | Connection as `sentinel_gateway` |

`completeness` also takes `--correlation-id <id>` (repeatable) for actions that must be present. The same check, `sentinel_audit.completeness.check_completeness`, works on the gateway's in-memory records too, so the scenario evaluation in US-26 can reuse it.

## With Docker Compose

`docker compose up` runs `migrate` once before the gateway starts. Afterwards:

```
docker compose run --rm audit verify-chain
docker compose run --rm audit completeness
```

## Tests

From the repository root: `py -m pytest services/audit-service -q`.

The PostgreSQL tests (the store, the role's privileges and the tamper test) need a server and an account that can create databases. They are skipped unless `AUDIT_TEST_DATABASE_URL` is set; CI starts PostgreSQL and sets it. To run them on your machine, start a throwaway server and point the tests at it:

```
docker run --rm -d --name audit-test-db -p 127.0.0.1:5433:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:0.8.7-pg17
$env:AUDIT_TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/postgres"
py -m pytest services/audit-service tests/acceptance -q
docker stop audit-test-db
```
