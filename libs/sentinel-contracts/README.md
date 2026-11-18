# Sentinel contracts

The messages that pass between Vera, the Sentinel Gateway, the protected tools and the audit trail, plus the two signed tokens: the session token that ties an action to a signed-in customer, and the execution token that lets one tool call through. Every service imports these instead of defining its own copy.

| | |
|---|---|
| First built in | Sprint 1 |
| Stories | US-18 (US-18.1 contracts, US-18.2 outcome and session token, US-18.4 tokens), used by US-16 and US-19 |
| Requirements | FR-01, FR-02, FR-05, FR-08, FR-09, FR-13; NFR-01, NFR-03, NFR-06 |
| Decision records | [ADR-010](../../docs/adr/ADR-010-shared-contracts-and-execution-tokens.md), [ADR-012](../../docs/adr/ADR-012-gateway-decision-pipeline.md) |

## What is in it

| Module | Contents |
|---|---|
| `sentinel_contracts.actions` | `ProtectedActionRequest` (what the agent proposes), `GovernanceDecision` (what the gateway decides), `ActionOutcome` and `ExecutionResult` (what the evaluate endpoint returns), and the `Decision`, `ReasonCode`, `Provenance`, `TaskType` and `ExecutionStatus` values |
| `sentinel_contracts.audit` | `AuditRecord`, one step in the life of an action before the audit service adds it to the hash chain, and `AuditEventType` |
| `sentinel_contracts.execution_token` | `issue_token` (gateway), `verify_token` and `ReplayGuard` (protected tools), `TOKEN_HEADER` |
| `sentinel_contracts.session_token` | `issue_session_token` (identity service), `verify_session_token` and `SessionClaims` (gateway), `SESSION_HEADER` |
| `sentinel_contracts.signing` | The signing code both tokens share |
| `sentinel_contracts.identifiers` | The identifier formats, such as `CUS-000123` and the correlation ID |

The field names and formats are the same as the ToolCall, AuditEvent and UserSession entities in `data/synthetic/models.py`. `tests/test_contracts_match_schema.py` at the repository root fails if they drift apart.

## Rules the contracts enforce

- Unknown fields are rejected, and a contract cannot be changed after it is created.
- Numbers must be finite. JSON has no NaN or infinity.
- Every provenance label must name an argument that exists.
- An ALLOW decision always carries an execution token; no other decision may carry one.
- A HUMAN_REVIEW decision always carries the approval request ID.
- Every decision has at least one reason code, with no repeats.
- An outcome carries an execution result exactly when the decision is ALLOW, and a result that did not succeed says why.

## How an execution token works

1. The gateway allows an action and calls `issue_token` with the correlation ID, tool name, exact arguments and customer. The token lives for 60 seconds.
2. The gateway forwards the call to the tool with the token in the `X-Execution-Token` header.
3. The tool calls `verify_token` with the tool name and the arguments it actually received. The token fails if the signature, audience, tool or arguments differ, or if it has expired.
4. The tool passes the claims to `ReplayGuard.consume`, which refuses any token already used.

The signing key is shared by the gateway and the tools through the `EXECUTION_TOKEN_KEY` setting. It must be at least 32 characters, and Vera must never have it. To create one:

```
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

## How a session token works

1. When a customer signs in, the identity service calls `issue_session_token` with the session, customer, agent and task. The token lasts 30 minutes by default and never more than 4 hours. In the demo, `python -m sentinel_gateway issue-session` does this.
2. Vera sends the token with every action in the `X-Session-Token` header.
3. The gateway calls `verify_session_token` and binds the action to what the token says, not to what the request body claims.

It is signed with `SESSION_TOKEN_KEY`, which must differ from `EXECUTION_TOKEN_KEY`, and its prefix is `s1` rather than `v1`, so neither token is ever accepted as the other. Vera must not have this key either.

## Tests

From the repository root: `py -m pytest libs/sentinel-contracts -q`
