# Sentinel Gateway

The Policy Enforcement Point. Every protected tool call passes through here and gets one decision: ALLOW, HUMAN_REVIEW, BLOCK or QUARANTINE.

| | |
|---|---|
| First built in | Sprint 1, extended in Sprints 2 and 3 |
| Stories | US-18, US-01, US-02a, US-02b, US-05 |
| Requirements | FR-01, FR-02, FR-03, FR-04, FR-05, FR-08, FR-09, FR-18; NFR-01, NFR-02, NFR-03 |

## What belongs here

- The evaluate endpoint and request and decision contracts
- Identity and scope checks, provenance tracking, decision orchestration
- Execution token signing

## Rules for this folder

- Deny by default. Fail closed when OPA or the risk engine is unavailable for a high-impact action.
- The risk score can add caution but never overturn a hard deny (ADR-003).
- Every decision writes an audit event.

Status: placeholder created in Sprint 0 (US-13.3). Replace this line when the first code lands.
