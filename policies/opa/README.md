# Bank policy as code

The bank's deterministic rules, written in Rego for Open Policy Agent (OPA): which tools each task allows, the ban on bulk export, and the refund amount rules. The Sentinel Gateway asks OPA about every action that passes its context checks and records the answer in the audit trail.

| | |
|---|---|
| First built in | Sprint 2 |
| Stories | US-02a; later US-02b (data-origin rule) and US-07 (Should) |
| Requirements | FR-03, FR-04, FR-06, FR-17; NFR-01, NFR-09 |
| Decision records | [ADR-002](../../docs/adr/ADR-002-opa-rego-policy.md), [ADR-015](../../docs/adr/ADR-015-bank-policy-in-opa.md) |

## Layout

| Path | What it holds |
|---|---|
| `.manifest` | The bundle's `revision`, which is the `policy_version` in every decision and audit event |
| `agentsentinel/data.json` | The settings and tables the rules use (see below) |
| `agentsentinel/gateway/decision.rego` | The decision document the gateway asks for, and the rule for incomplete input |
| `agentsentinel/gateway/tools.rego` | Bulk export, and which tools an agent and a task allow |
| `agentsentinel/gateway/amounts.rego` | Refund amounts: format, range and the automatic limit |
| `agentsentinel/gateway/*_test.rego` | Unit tests. OPA's server does not load them |
| `Dockerfile` | The OPA image Docker Compose runs |

## What the gateway sends and gets back

The gateway posts to `/v1/data/agentsentinel/gateway/decision?provenance=true` with this input:

```json
{
  "agent": {"agent_id": "AGT-001", "name": "Vera", "allowed_tools": ["get_customer", "..."]},
  "tool": {"tool_name": "issue_refund", "category": "financial", "high_impact": true, "sensitive_parameters": ["account_id", "amount"]},
  "action": {"task_type": "refund_request", "tool_name": "issue_refund", "customer_scope": "CUS-000123", "arguments": {"amount": "120.00", "...": "..."}, "provenance_labels": {"amount": "trusted_user_input"}}
}
```

OPA answers with every rule the action breaks. No violations means the policy has no objection; the gateway's other checks still run.

```json
{"violations": [{"rule": "bulk_export", "decision": "BLOCK", "reason": "POLICY_DENY", "message": "Exporting customer records in bulk is never allowed through an agent."}]}
```

The gateway takes the strongest decision, keeps every reason code, uses the leading rule's message as the summary, and records the rule names and the bundle's revision.

## The rules

The rule IDs on the right are the ones in `data/synthetic/labelling-rules.md`, so the dataset labels and the live policy follow the same rules.

| Rule | Decision | Reason code | When | Labelling rule |
|---|---|---|---|---|
| `incomplete_input` | BLOCK | `MISSING_CONTEXT` | The input lacks the tool, the task, the arguments or the agent's allowlist | Deny by default |
| `bulk_export` | BLOCK | `POLICY_DENY` | The tool is in `bulk_export_tools`, whatever the task or the agent | R1 |
| `tool_not_allowed_for_agent` | BLOCK | `TOOL_NOT_ALLOWED` | The tool is not in the agent's `allowed_tools` | R2 |
| `tool_not_allowed_for_task` | BLOCK | `TOOL_NOT_ALLOWED` | The task's list in `task_tools` does not include the tool | R2 |
| `refund_amount_format` | BLOCK | `INVALID_ARGUMENTS` | The amount is missing, not a string, or not a number with at most two decimal places | R3 |
| `refund_amount_not_positive` | BLOCK | `INVALID_ARGUMENTS` | The amount is zero or negative | R3 |
| `refund_above_hard_cap` | BLOCK | `REFUND_OVER_LIMIT` | The amount is above the hard cap | R3 |
| `refund_above_automatic_limit` | HUMAN_REVIEW | `REFUND_OVER_LIMIT` | The amount is above the automatic limit and at or below the hard cap | R6 |

Until the approval service arrives in US-03, the gateway blocks a HUMAN_REVIEW decision with `DEPENDENCY_UNAVAILABLE`, so a refund above 200.00 USD does not run.

## Policy data

`agentsentinel/data.json` holds:

- `settings`: the refund limits and the sequence settings confirmed on 10 November 2026, the same values as the settings table in `data/synthetic/labelling-rules.md`. `tests/test_policy_matches_bank.py` fails if the two disagree.
- `task_tools`: the tools each task allows (below).
- `bulk_export_tools`: tools that are never allowed through an agent.
- `refund_amount_argument`: which argument holds the amount, for each tool that pays money out.

Which tools each agent may use is not here: it is the agent's `allowed_tools` in the gateway's `agents.json`, sent with every action.

The Product Owner confirmed the tools for each task on 23 November 2026:

| Task | Tools |
|---|---|
| `account_inquiry` | `get_customer`, `get_accounts`, `get_transactions` |
| `refund_request` | `get_customer`, `get_accounts`, `get_transactions`, `issue_refund` |
| `profile_update` | `get_customer`, `update_address` |
| `dispute` | `get_customer`, `get_accounts`, `get_transactions`, `close_dispute`, `freeze_account` |
| `admin_maintenance` | `export_customers`, `reset_credentials`, `freeze_account` |

A refund is only issued in a refund request. `freeze_account` is allowed in a dispute, so that when a customer reports a suspected fraudulent transaction, Vera can freeze the account first and stop any further debits.

## Changing a rule or a setting

1. Change the Rego or `data.json`, and add or change a test for it, including the boundary values.
2. Raise `revision` in `.manifest`: the patch number for a wording change, the minor number for a new or changed rule or setting, the major number when the input or output shape changes.
3. If a setting also appears in `data/synthetic/labelling-rules.md`, change it there too. If the change alters any label in the risk model's dataset, `tests/test_dataset.py` fails until a new dataset version is frozen: see "Freezing and changing the dataset" in `data/synthetic/dataset/README.md` (US-21).
4. Open a pull request. The Product Owner approves any change to what is allowed.

## Running the tests

Install OPA 1.22.4, the version in the Dockerfile and in CI: download `opa_windows_amd64.exe` (or the build for your system) from https://github.com/open-policy-agent/opa/releases/tag/v1.22.4, rename it to `opa.exe` and put it in a folder on your PATH. Then, from the repository root:

```
opa fmt --list --fail policies/opa
opa check --strict policies/opa
opa test policies/opa -v
opa test policies/opa --coverage --threshold 100
```

CI runs the same four commands. The gateway's policy tests and the acceptance tests also start a real OPA server with this folder (`opa_url` in the repository's `conftest.py`). Without the `opa` command they are skipped on your machine; in CI they fail instead.

## Running OPA

`Dockerfile` in this folder builds the OPA image: OPA's statically linked binary on the official busybox image, with the policies copied in. Docker Compose builds and starts it and checks `/health?bundles=true`, which answers only once the bundle is loaded. The official OPA images cannot run that check themselves: they have no `wget`.

```
docker build -f policies/opa/Dockerfile -t agentsentinel/opa .
docker run --rm -p 8181:8181 agentsentinel/opa
```

Or with the `opa` command, from the repository root:

```
opa run --server --addr=127.0.0.1:8181 --bundle --ignore=*_test.rego policies/opa
```

OPA must serve the folder as a bundle (`--bundle`). Otherwise it reports no revision, and the gateway blocks every action with `DEPENDENCY_UNAVAILABLE`, because it will not record a decision without the policy version.
