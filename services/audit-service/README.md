# Audit and incident service

Stores the hash-linked audit trail and builds incident timelines by correlation ID.

| | |
|---|---|
| First built in | Sprint 1, extended in Sprint 3 |
| Stories | US-19, US-06b |
| Requirements | FR-13, FR-14; NFR-06, NFR-11 |

## What belongs here

- Audit event storage, the verify-chain command and the timeline API

## Rules for this folder

- Audit rows are append-only. The service's database role cannot update or delete them.
- The hash rule is in `data/synthetic/README.md`.

Status: placeholder created in Sprint 0 (US-13.3). Replace this line when the first code lands.
