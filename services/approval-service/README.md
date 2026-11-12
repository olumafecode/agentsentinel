# Approval service

Creates, expires, approves and rejects held actions so that a person stays in control of high-impact decisions.

| | |
|---|---|
| First built in | Sprint 3 |
| Stories | US-03 |
| Requirements | FR-10, FR-11; NFR-01, NFR-12 |

## What belongs here

- Approval request storage and the approve and reject endpoints
- Maker-checker rules

## Rules for this folder

- The person who raised a request cannot approve it.
- A held action resumes or ends under the same correlation ID.

Status: placeholder created in Sprint 0 (US-13.3). Replace this line when the first code lands.
