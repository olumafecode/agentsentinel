# RAG explanation service

After a decision is made, retrieves bank policy passages and writes a plain-English explanation that cites policy section IDs.

| | |
|---|---|
| First built in | Sprint 2 |
| Stories | US-06a |
| Requirements | FR-12; NFR-02, NFR-07 |

## What belongs here

- Policy ingestion, retrieval and the explain endpoint
- Citation validation and the mock fallback

## Rules for this folder

- Runs after the decision and can never change it (ADR-004).
- A citation that was not retrieved is rejected.

Status: placeholder created in Sprint 0 (US-13.3). Replace this line when the first code lands.
