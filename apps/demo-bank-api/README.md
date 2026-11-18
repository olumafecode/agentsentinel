# Demo bank API

The fictional bank whose tools Vera asks to use. It holds synthetic customers, accounts, transactions and disputes, and it runs a tool only when the call carries a gateway-signed execution token for exactly that call. Everything else gets HTTP 403.

| | |
|---|---|
| First built in | Sprint 1 |
| Stories | US-16 (tasks US-16.1 to US-16.4), US-01.1 (ownership lookup) |
| Requirements | NFR-08, NFR-10 |
| Decision records | [ADR-001](../../docs/adr/ADR-001-independent-gateway.md), [ADR-010](../../docs/adr/ADR-010-shared-contracts-and-execution-tokens.md), [ADR-011](../../docs/adr/ADR-011-demo-bank-in-memory.md) |

## Endpoints

| Method and path | Token needed | What it does |
|---|---|---|
| `GET /healthz` | No | Liveness: the process is up |
| `GET /readyz` | No | Readiness: data loaded, with record counts |
| `GET /v1/tools` | No | Lists every tool, its category, whether it is high impact, its sensitive parameters and its argument schema |
| `POST /v1/tools/{tool_name}` | Yes | Runs one tool; the JSON body is the tool's arguments |
| `POST /v1/internal/owners` | Yes, for `resolve_owners` | Gateway only. Says which customer owns each account, transaction or dispute in `{"identifiers": [...]}`; unknown records map to `null`. Not in the tool list |
| `POST /admin/reset` | Admin key | Returns the bank to its seeded state; disabled unless `DEMO_ADMIN_KEY` is set |
| `GET /docs` | No | Interactive API documentation |

## Tools

| Tool | Category | High impact | Sensitive parameters | Arguments |
|---|---|---|---|---|
| `get_customer` | read | No | | `customer_id` |
| `get_accounts` | read | No | | `customer_id` |
| `get_transactions` | read | No | | `customer_id`, `limit` (1 to 100, default 20) |
| `update_address` | write | No | `address` | `customer_id`, `address` |
| `issue_refund` | financial | Yes | `account_id`, `amount` | `account_id`, `amount` (string such as `"120.00"`), `original_transaction_id`, `reason` |
| `close_dispute` | write | No | | `dispute_id`, `resolution` |
| `export_customers` | export | Yes | | none (send `{}`) |
| `reset_credentials` | admin | Yes | `customer_id` | `customer_id` |
| `freeze_account` | admin | Yes | `account_id` | `account_id`, `reason` |

The bank checks that a call is well formed and possible: the purchase exists, the refund is not larger than what is left to refund, the account is open. It does not judge intent. A refund to an account in the attacker range is possible here on purpose; stopping it is the gateway's job (UC-02).

## Responses

Success: `{"tool_name": ..., "correlation_id": ..., "result": ...}`, where the correlation ID comes from the token.

Failure: `{"error": {"code": ..., "message": ...}}`.

| Status | Codes |
|---|---|
| 400 | `invalid_json` |
| 403 | `missing_token`, `token_signature_invalid`, `token_expired`, `token_tool_mismatch`, `token_arguments_mismatch`, `token_replayed`, `token_audience_mismatch` and the other token checks; `invalid_admin_key` |
| 404 | `unknown_tool`, `customer_not_found`, `account_not_found`, `transaction_not_found`, `dispute_not_found` |
| 409 | `refund_exceeds_original`, `not_refundable`, `account_not_open`, `dispute_already_closed`, `account_closed` |
| 413 | `body_too_large` |
| 422 | `invalid_arguments`, with the problems under `details` |

## Data

The seed (default `20261109`) always produces the same bank: 43 customers, 63 accounts, 712 transactions and 7 disputes. These named records are always present for demos and tests:

| Record | Use |
|---|---|
| `CUS-000123` Avery Stone, account `ACC-00000123` | The main demo customer |
| `TXN-0000004567` purchase of 750.00 | Refund above the 200.00 automatic limit (UC-03) |
| `TXN-0000004568` purchase of 120.00 | Refund within the limit |
| `DSP-000001` open dispute | Closing a dispute |
| `CUS-000456` Jordan Reyes, account `ACC-00000456` | The other customer in cross-customer tests (UC-04) |
| `ACC-99000017`, `ACC-99000042` | Attacker accounts for prompt-injection tests (UC-02) |

The data lives in memory (ADR-011): a restart or a reset returns the bank to exactly this state.

## Settings

| Variable | Required | Meaning |
|---|---|---|
| `EXECUTION_TOKEN_KEY` | Yes | Signing key shared with the gateway, at least 32 characters. The bank will not start without it |
| `DEMO_ADMIN_KEY` | No | At least 16 characters. Enables `POST /admin/reset` |
| `BANK_SEED` | No | Seed for the synthetic data; default 20261109 |

Keep real values in a `.env` file, which git ignores. Never commit them.

## Run it on your machine

From the repository root, once:

```
py -m pip install -r requirements-dev.txt
py -m pip install --no-deps -e libs/sentinel-contracts -e apps/demo-bank-api
```

Then, in PowerShell:

```
$env:EXECUTION_TOKEN_KEY = py -c "import secrets; print(secrets.token_urlsafe(48))"
$env:DEMO_ADMIN_KEY = "local-admin-key-change-me"
py -m uvicorn demo_bank_api.main:create_app --factory --port 8001
```

Open http://localhost:8001/docs to see the endpoints. To reset a running bank from another terminal with the same `DEMO_ADMIN_KEY`:

```
py -m demo_bank_api reset
```

To see the record counts and the seeded checksum without starting the server: `py -m demo_bank_api seed-info`.

## Run it in Docker

From the repository root:

```
docker build -f apps/demo-bank-api/Dockerfile -t agentsentinel/demo-bank-api .
docker run --rm -p 8001:8001 -e EXECUTION_TOKEN_KEY=<key> -e DEMO_ADMIN_KEY=<admin key> agentsentinel/demo-bank-api
```

The image runs as a non-root user (UID 10001) and reports its health from `/healthz`.

## Tests

From the repository root: `py -m pytest apps/demo-bank-api -q`
