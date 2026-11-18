# Sentinel contracts

The messages that pass between Vera, the Sentinel Gateway and the protected tools, plus the signed execution token that lets a tool call through. Every service imports these instead of defining its own copy.

| | |
|---|---|
| First built in | Sprint 1 |
| Stories | US-18 (task US-18.1 contracts, groundwork for US-18.4 tokens), used by US-16 |
| Requirements | FR-01, FR-02, FR-05, FR-08, FR-09; NFR-01, NFR-03 |
| Decision record | [ADR-010](../../docs/adr/ADR-010-shared-contracts-and-execution-tokens.md) |

## What is in it

| Module | Contents |
|---|---|
| `sentinel_contracts.actions` | `ProtectedActionRequest` (what the agent proposes), `GovernanceDecision` (what the gateway answers), and the `Decision`, `ReasonCode`, `Provenance` and `TaskType` values |
| `sentinel_contracts.execution_token` | `issue_token` (gateway), `verify_token` and `ReplayGuard` (protected tools), `TOKEN_HEADER` |
| `sentinel_contracts.identifiers` | The identifier formats, such as `CUS-000123` and the correlation ID |

The field names and formats are the same as the ToolCall entity in `data/synthetic/models.py`. `tests/test_contracts_match_schema.py` at the repository root fails if the two drift apart.

## Rules the contracts enforce

- Unknown fields are rejected, and a contract cannot be changed after it is created.
- Every provenance label must name an argument that exists.
- An ALLOW decision always carries an execution token; no other decision may carry one.
- A HUMAN_REVIEW decision always carries the approval request ID.
- Every decision has at least one reason code, with no repeats.

## How an execution token works

1. The gateway allows an action and calls `issue_token` with the correlation ID, tool name, exact arguments and customer. The token lives for 60 seconds.
2. The gateway forwards the call to the tool with the token in the `X-Execution-Token` header.
3. The tool calls `verify_token` with the tool name and the arguments it actually received. The token fails if the signature, audience, tool or arguments differ, or if it has expired.
4. The tool passes the claims to `ReplayGuard.consume`, which refuses any token already used.

The signing key is shared by the gateway and the tools through the `EXECUTION_TOKEN_KEY` setting. It must be at least 32 characters, and Vera must never have it. To create one:

```
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Tests

From the repository root: `py -m pytest libs/sentinel-contracts -q`
