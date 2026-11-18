# Sentinel Gateway

The Policy Enforcement Point. Every protected action Vera proposes comes here first and gets one decision: ALLOW, HUMAN_REVIEW, BLOCK or QUARANTINE. Only an allowed action reaches the bank, and the gateway forwards it itself with a single-use execution token.

| | |
|---|---|
| First built in | Sprint 1, extended in Sprints 2 and 3 |
| Stories | US-18 (tasks US-18.2 to US-18.6), US-01 (US-01.1 to US-01.4); later US-02a, US-02b, US-03, US-04, US-05 |
| Requirements | FR-01, FR-02, FR-03, FR-08, FR-09, FR-13; NFR-01, NFR-02, NFR-03, NFR-06 |
| Decision records | [ADR-001](../../docs/adr/ADR-001-independent-gateway.md), [ADR-003](../../docs/adr/ADR-003-ml-risk-advisory.md), [ADR-010](../../docs/adr/ADR-010-shared-contracts-and-execution-tokens.md), [ADR-012](../../docs/adr/ADR-012-gateway-decision-pipeline.md), [ADR-013](../../docs/adr/ADR-013-ownership-lookup.md) |

## What happens to one action

1. The agent's API key identifies the agent. A missing or wrong key gets HTTP 401.
2. The session token is verified. The agent ID, session, customer and task in the request must match it and the key.
3. The checks run in stage order and the orchestrator combines their findings. If the action names an account, transaction or dispute, the customer scope check asks the bank who owns it.
4. `action_received` and `decision_made` are written to the audit trail. If that fails, nothing runs (HTTP 503).
5. For ALLOW, the gateway signs an execution token for exactly this call and calls the bank.
6. `action_executed`, `approval_requested` or `action_stopped` is written, and the outcome is kept under the correlation ID.

## Endpoints

| Method and path | What it does |
|---|---|
| `POST /v1/actions/evaluate` | Decides on one action and, if it is allowed, runs it at the bank |
| `GET /healthz` | Liveness: the process is up |
| `GET /readyz` | Readiness: the agent and tool registries are loaded, and which checks run |
| `GET /docs` | Interactive API documentation |

## Calling the evaluate endpoint

Headers:

| Header | Value |
|---|---|
| `Authorization` | `Bearer <agent key>` |
| `X-Session-Token` | The customer's session token. Without one the action is blocked |

The body is a `ProtectedActionRequest` from `libs/sentinel-contracts`:

```json
{
  "correlation_id": "3f2b8c1e-5a7d-4e9b-9c1a-2d4f6a8b0c1e",
  "session_id": "SES-00000042",
  "agent_id": "AGT-001",
  "customer_scope": "CUS-000123",
  "task_type": "refund_request",
  "tool_name": "issue_refund",
  "arguments": {"account_id": "ACC-00000123", "amount": "120.00", "original_transaction_id": "TXN-0000004568", "reason": "Duplicate charge"},
  "provenance_labels": {"account_id": "trusted_user_input", "amount": "trusted_user_input"},
  "requested_at": "2027-01-15T08:00:00Z"
}
```

The response is an `ActionOutcome`: `{"decision": {...}, "execution": {...}}`. `execution` is present only for ALLOW and holds the bank's result, or why the bank refused or could not be reached. The `X-Correlation-ID` response header repeats the correlation ID.

Every JSON object gets a decision with HTTP 200, even a malformed one, which is blocked. These are the only other answers:

| Status | Code | When |
|---|---|---|
| 400 | `invalid_json` | The body is not a JSON object |
| 401 | `missing_agent_key`, `invalid_agent_key` | No agent key, or one the gateway does not know |
| 409 | `correlation_id_conflict` | The correlation ID was already used for a different request |
| 413 | `body_too_large` | The body is larger than 64 KB |
| 503 | `audit_unavailable` | The decision could not be audited, so nothing ran. Safe to retry |

## Same correlation ID twice

Send the identical request again, for example after a timeout, and you get the stored outcome with `X-Idempotent-Replay: true`. Nothing is evaluated or run again, so a refund pays once. The same ID with any other body, session token or agent gets HTTP 409. Outcomes are kept for an hour; a request stamped more than 5 minutes ago is blocked as stale anyway.

## Checks

| Check | Stage | Objects with |
|---|---|---|
| `context_binding` | CONTEXT | BLOCK `IDENTITY_MISMATCH` when the request does not match the agent key or the session; BLOCK `MISSING_CONTEXT` when there is no session or it has expired |
| `agent_status` | CONTEXT | QUARANTINE `AGENT_QUARANTINED`; BLOCK `AGENT_DISABLED`; BLOCK `IDENTITY_MISMATCH` for an unregistered agent |
| `request_freshness` | CONTEXT | BLOCK `STALE_REQUEST` when `requested_at` is over 5 minutes old or over 30 seconds ahead |
| `known_tool` | CONTEXT | BLOCK `UNKNOWN_TOOL` for a tool missing from `data/tools.json` |
| `tool_allowlist` | HARD_RULE | BLOCK `TOOL_NOT_ALLOWED` when the tool is not in the agent's `allowed_tools`, or the session's task is not in the tool's `allowed_task_types` |
| `customer_scope` | HARD_RULE | BLOCK `OUTSIDE_CUSTOMER_SCOPE` when any customer, account, transaction or dispute ID in the arguments belongs to another customer or does not exist |

A request that fails validation is blocked with `MISSING_CONTEXT`, `UNKNOWN_TOOL` or `INVALID_ARGUMENTS`. A check that raises an error blocks with `DEPENDENCY_UNAVAILABLE`. When checks disagree, QUARANTINE beats BLOCK, which beats HUMAN_REVIEW (ADR-012).

## Customer scope

Every argument value that is a customer, account, transaction or dispute ID is checked, whatever the argument is called and however deeply it is nested. Customer IDs are compared with the session's customer. For the other records the gateway asks the bank's internal lookup, `POST /v1/internal/owners`, with its own single-use token (ADR-013). Vera cannot call that lookup, because it cannot sign a token.

- A lookup by customer ID never calls the bank, so AT-02 proves the bank receives nothing.
- A record the bank does not know is out of scope.
- If the lookup fails, the action is blocked with `DEPENDENCY_UNAVAILABLE`.
- If an earlier check has already blocked the action, the bank is not asked at all.
- The decision's summary names the records but never the customer who owns them. The audit record keeps both.

## Adding a check

Subclass `Check` in a module for its story (`scope.py` holds the US-01 rules), give it a name and a stage, and add it to `default_checks()` in `pipeline.py`:

```python
class BulkExportCheck(Check):
    name = "bulk_export"
    stage = Stage.HARD_RULE

    def evaluate(self, context, earlier):
        if context.request.tool_name == "export_customers":
            return objection(
                Decision.BLOCK,
                ReasonCode.POLICY_DENY,
                summary="Bulk export is not allowed.",
            )
        return NO_OBJECTION
```

A check that needs a client, as `CustomerScopeCheck` needs the ownership lookup, takes it in its constructor, and `default_checks()` passes it in. Nothing else changes: the orchestrator places the check by stage, applies the precedence order and records its result in the audit trail.

## Agents and tools

`src/sentinel_gateway/data/agents.json` lists the agents and `data/tools.json` the bank tools, in the shape of the Agent and ToolDefinition entities in `data/synthetic/models.py`. `tests/test_gateway_matches_bank.py` at the repository root fails if the tool list drifts from the demo bank's catalogue.

## Settings

| Variable | Required | Meaning |
|---|---|---|
| `EXECUTION_TOKEN_KEY` | Yes | The same key the bank has, at least 32 characters |
| `SESSION_TOKEN_KEY` | Yes | Key for customer session tokens, at least 32 characters and different from `EXECUTION_TOKEN_KEY` |
| `AGENT_KEYS` | Yes | `AGT-001:<key>`, with a comma between agents. Each key at least 32 characters, and every agent must be in `agents.json` |
| `BANK_URL` | No | Default `http://localhost:8001` |
| `BANK_TIMEOUT_SECONDS` | No | Default 5 |

Create any key with `py -m sentinel_gateway new-key`. Keep real values in a `.env` file, which git ignores. Never commit them, and never give `SESSION_TOKEN_KEY` or `EXECUTION_TOKEN_KEY` to Vera.

## Run it on your machine

From the repository root, once:

```
py -m pip install -r requirements-dev.txt
py -m pip install --no-deps -e libs/sentinel-contracts -e apps/demo-bank-api -e services/sentinel-gateway
```

Start the bank first (see `apps/demo-bank-api/README.md`), then in a second PowerShell window with the bank's `EXECUTION_TOKEN_KEY` set:

```
$env:SESSION_TOKEN_KEY = py -m sentinel_gateway new-key
$env:VERA_KEY = py -m sentinel_gateway new-key
$env:AGENT_KEYS = "AGT-001:$env:VERA_KEY"
py -m uvicorn sentinel_gateway.main:create_app --factory --port 8000
```

To try an action from a third window with the same three variables:

```
$session = py -m sentinel_gateway issue-session --customer CUS-000123 --task account_inquiry --session SES-00000042
$body = @{
    correlation_id    = [guid]::NewGuid().ToString()
    session_id        = "SES-00000042"
    agent_id          = "AGT-001"
    customer_scope    = "CUS-000123"
    task_type         = "account_inquiry"
    tool_name         = "get_transactions"
    arguments         = @{ customer_id = "CUS-000123"; limit = 2 }
    provenance_labels = @{ customer_id = "system" }
    requested_at      = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json
$headers = @{ Authorization = "Bearer $env:VERA_KEY"; "X-Session-Token" = $session }
Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/actions/evaluate -ContentType application/json -Headers $headers -Body $body | ConvertTo-Json -Depth 8
```

Audit records are printed as one JSON line each in the gateway's window until the audit service (US-19) takes them.

## Run it in Docker

From the repository root:

```
docker build -f services/sentinel-gateway/Dockerfile -t agentsentinel/sentinel-gateway .
docker run --rm -p 8000:8000 -e EXECUTION_TOKEN_KEY=<key> -e SESSION_TOKEN_KEY=<key> -e AGENT_KEYS=AGT-001:<key> -e BANK_URL=http://host.docker.internal:8001 agentsentinel/sentinel-gateway
```

The image runs as a non-root user (UID 10001) and reports its health from `/healthz`.

## Tests

From the repository root: `py -m pytest services/sentinel-gateway -q`. The tests run the real demo bank in the same process, so they cover the whole path from decision to bank, including a replayed token, a token reused for another call, retries of the same refund, two identical refunds arriving at once, and a refund sent to another customer's account.

The acceptance tests AT-01 and AT-02 are in `tests/acceptance` at the repository root: `py -m pytest tests/acceptance -q`.
