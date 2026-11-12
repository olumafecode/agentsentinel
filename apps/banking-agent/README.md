# Banking agent (Vera)

Vera, the AI banking agent whose actions AgentSentinel governs. It plans tasks and proposes tool calls. It runs in a scripted mode for repeatable demos and in a live LLM mode through a provider adapter.

| | |
|---|---|
| First built in | Sprint 1 (scripted), Sprint 4 (live LLM) |
| Stories | US-17, US-24 |
| Requirements | FR-01; NFR-14 |

## What belongs here

- Agent loop, tool schemas and the gateway client
- Scripted fixtures for the use cases
- The scenario runner

## Rules for this folder

- Vera is configured with the gateway address only. It never holds a bank API address or credential (ADR-001).
- All LLM access goes through the adapter (ADR-007).

Status: placeholder created in Sprint 0 (US-13.3). Replace this line when the first code lands.
