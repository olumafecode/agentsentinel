# Banking agent (Vera)

Vera, the AI banking agent whose actions AgentSentinel governs. She turns what a customer asks into tool calls and proposes each one to the Sentinel Gateway, which decides. She never calls the bank herself. In scripted mode her tool calls come from a scenario, so every run is the same; the live language model arrives in Sprint 4.

| | |
|---|---|
| First built in | Sprint 1 (scripted), Sprint 4 (live LLM) |
| Stories | US-17 (tasks US-17.1 to US-17.4), US-24 |
| Requirements | FR-01; NFR-14 |
| Decision records | [ADR-001](../../docs/adr/ADR-001-independent-gateway.md), [ADR-007](../../docs/adr/ADR-007-external-llm-adapter.md), [ADR-012](../../docs/adr/ADR-012-gateway-decision-pipeline.md) |

## What Vera holds

| Setting | Meaning |
|---|---|
| `GATEWAY_URL` | Where the gateway is; default `http://localhost:8000` |
| `VERA_AGENT_KEY` | Her own API key for the gateway |
| `VERA_AGENT_ID` | Default `AGT-001` |

Nothing else. She has no bank address, no execution token key and no session key, and settings for other services are ignored even when they are set. The customer's session token comes from the chat channel with each conversation.

## How she behaves

For every customer message, a planner gives Vera the tool calls to make. She proposes them one at a time:

| Decision | What Vera does |
|---|---|
| ALLOW | Tells the customer the result and carries on |
| HUMAN_REVIEW | Says the request is waiting for a member of staff, and stops this turn |
| BLOCK | Says the action was refused, and stops this turn. She never proposes the same call again in the conversation |
| QUARANTINE | Says she cannot continue, and proposes nothing more |

If the gateway cannot be reached, she says nothing was done. A call that got lost on the way is sent again unchanged, which is safe because the gateway answers a repeated correlation ID with the stored outcome. If the gateway refuses Vera herself, for example because of a wrong key, she ends the conversation.

The planner is an interface (`planning.Planner`). Scripted mode plays back a scenario; the language model in US-24 will be another planner, so the loop stays the same.

## Scenarios

One scripted scenario per use case, in `src/banking_agent/scenarios`:

| Scenario | Expected | Status |
|---|---|---|
| UC-01 Allow safe customer lookup | ALLOW | Active |
| UC-02 Block prompt-injected refund | BLOCK, and no retry | Active (blocked by customer scope; US-02b adds the untrusted-origin rule) |
| UC-03 Hold high-value refund | HUMAN_REVIEW | Pending on US-03 |
| UC-04 Deny cross-customer access | BLOCK, then ALLOW for her own data | Active |
| UC-05 Block bulk export | BLOCK | Active (bank policy in OPA, US-02a) |
| UC-06 Detect behavioral anomaly | BLOCK on the fifth quick refund | Pending on US-04 |
| UC-07 Quarantine repeated violations | QUARANTINE on the third violation | Pending on US-05 |

Each scripted call says what the gateway should decide, or that Vera must not propose it at all. The runner skips pending scenarios unless asked, because their actions may still be allowed and would change the bank. When a story lands, set its scenario to `"status": "active"` and remove `pending_on`.

## Run the scenarios

Against the Compose stack, from the repository root:

```
docker compose run --rm vera
```

Or from your machine against a running gateway, with the same values as in `.env`:

```
$env:GATEWAY_URL = "http://localhost:8000"
$env:VERA_AGENT_KEY = "<VERA_AGENT_KEY>"
$env:SESSION_TOKEN_KEY = "<SESSION_TOKEN_KEY>"
py -m banking_agent run              # every active scenario
py -m banking_agent run UC-04        # one scenario
py -m banking_agent run --include-pending
py -m banking_agent list
```

The runner also plays the customer's sign-in, so it needs `SESSION_TOKEN_KEY`. Vera herself never receives it. The exit code is 1 if an active scenario fails.

## Tool schemas

`src/banking_agent/data/tools.json` describes the seven tools Vera may propose, copied from the bank's `GET /v1/tools`. The language model sees these in live mode. `tests/test_vera_matches_bank.py` at the repository root fails if they drift from the bank or from Vera's `allowed_tools` in the gateway.

## Tests

From the repository root: `py -m pytest apps/banking-agent -q`. These use a fake gateway. `tests/acceptance` at the root runs every active scenario against the real gateway and bank.
