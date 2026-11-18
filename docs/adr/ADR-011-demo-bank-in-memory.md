# ADR-011: The demo bank keeps its data in memory

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-18 |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | NFR-08, NFR-13, NFR-14 |
| Stories | US-16, US-27 |

## Context

The demo bank stands in for a real bank's systems so that Vera has tools to call. It is not part of AgentSentinel. Demos, scenario tests and the AgentDojo runs need it to start from the same known state every time, and to return to that state quickly after a scenario has moved money or frozen an account.

ADR-005 chose PostgreSQL for AgentSentinel's own records: the audit trail, approvals, incidents and policy embeddings. This ADR settles where the demo bank's data lives.

## Decision

- The demo bank builds its data from a fixed seed at start-up and keeps it in memory behind one class, `BankStore`, with a lock around every read and change.
- `POST /admin/reset` (and `python -m demo_bank_api reset`) rebuilds the data from the seed. It needs the `DEMO_ADMIN_KEY` value and is disabled when that setting is absent.
- The bank runs as a single replica.
- ADR-005 still applies to everything AgentSentinel itself records.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| Store the bank's data in the shared PostgreSQL | Rejected for now. It adds tables, migrations and a database dependency to tests for data that should be thrown away after every scenario. |
| A SQLite file per bank instance | Rejected. It survives restarts, which is the opposite of what a demo needs, and adds file handling in containers. |

## Consequences

What we gain:

- Every start and every reset gives exactly the same bank, which the seeded checksum proves.
- Bank tests need no database and run in about two seconds.

What it costs:

- A restart loses changes made during a session. For a demo bank this is intended.
- The bank cannot scale beyond one replica without moving its data to a shared store. Only the gateway is scaled in the Kubernetes profile, so this is acceptable.
- `BankStore` is the only class that touches the data, so moving to PostgreSQL later would replace that class without changing the tools or the API.
