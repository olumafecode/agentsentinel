# Demo bank API

The fictional bank: synthetic customers, accounts, transactions, refunds and admin tools that Vera asks to use.

| | |
|---|---|
| First built in | Sprint 1 |
| Stories | US-16 |
| Requirements | NFR-08, NFR-10 |

## What belongs here

- FastAPI service with the bank tools
- Seed generator and the demo reset command

## Rules for this folder

- Protected endpoints accept a request only with a valid gateway-signed single-use token.
- Synthetic data only, following `data/synthetic/README.md`.

Status: placeholder created in Sprint 0 (US-13.3). Replace this line when the first code lands.
