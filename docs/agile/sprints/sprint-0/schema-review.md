# Sprint 0 schema review (US-15.4)

**Reviewer (Code Owner):**  
**Date of review:**  
**Reviewed at commit:** (paste the short commit ID from `git log --oneline -1`)  

## What was reviewed

- `data/synthetic/models.py` (schema version 1.0.0)
- `data/synthetic/README.md`, `data/synthetic/labelling-rules.md`, `data/synthetic/examples.json`
- `tests/test_synthetic_schema.py`

## How to do the review

1. Run `py -m pytest tests/test_synthetic_schema.py -q` and record the result below.
2. Read `data/synthetic/README.md` from top to bottom.
3. For each row in the checklist, open the file named in "Where to look", confirm the statement is true and write Pass or Gap.
4. Write any problem you find in the Findings table, even a small one.
5. Record the decision. Each follow-up becomes an item on the board.

**Test result:** __ passed, __ failed

## Checklist

### FR-04: validate structured action details (amount, account identifier, target resource, allowed ranges)

| Check | Where to look | Result | Notes |
|---|---|---|---|
| Amounts have two decimals and transactions must be positive | `Money` type; `Transaction.amount` | | |
| Balances cannot be negative | `Account.balance` | | |
| Customer, account and transaction identifiers have one fixed format each | `CustomerId`, `AccountId`, `TransactionId` at the top of `models.py` | | |
| The target of an action is explicit | `ToolCall.customer_scope`, `ToolCall.arguments` | | |
| A refund names the transaction it refunds | `Transaction.refund_points_to_a_purchase` | | |
| Allowed ranges (200.00 USD automatic limit, 5,000.00 USD hard cap) are defined in one place | `labelling-rules.md`, "Settings the rules use" | | |

Known follow-up to judge: `ToolCall.arguments` accepts any structured values. The exact arguments each tool takes are defined with the tools in US-16 and checked by the gateway in US-18, and the ranges are enforced by OPA in US-02a. Decide whether that split is acceptable for Sprint 0.

### FR-05: record data provenance for sensitive parameters

| Check | Where to look | Result | Notes |
|---|---|---|---|
| Every argument can carry an origin label | `ToolCall.provenance_labels` | | |
| The three origins separate customer intent from retrieved content | `Provenance` enumeration | | |
| A label cannot point at an argument that does not exist | `ToolCall.labels_refer_to_arguments` | | |
| Each tool declares which of its parameters are sensitive | `ToolDefinition.sensitive_parameters` | | |
| Attacker accounts in test scenarios are easy to recognize | Rule 10 in `README.md` | | |

Known follow-up to judge: the schema does not force every sensitive parameter to have a label, because that needs the tool definition and the tool call together. The gateway will treat a missing label on a sensitive parameter as untrusted (US-02b). Decide whether to accept this or ask for a schema check.

### FR-07: risk score for actions and short sequences

| Check | Where to look | Result | Notes |
|---|---|---|---|
| Every dataset row has an expected outcome, a failure mode and the rule that set them | `LabelledActionEvent` | | |
| Actions are grouped into ordered sequences | `sequence_id`, `position` | | |
| The train, validation and test split is recorded on each row | `split` | | |
| A blocked or quarantined row must name a failure mode | `LabelledActionEvent.normal_actions_are_allowed` | | |
| The model's output can be stored with its versions | `RiskAssessment` | | |

The six feature families in proposal Section 8.1 must be derivable from the schema:

| Feature family | Fields that supply it | Result |
|---|---|---|
| Identity and context | `Agent.role`, `ToolCall.task_type`, `ToolCall.customer_scope` against `UserSession.customer_id`, `ToolDefinition.category` | |
| Action | `ToolCall.tool_name`, `ToolCall.arguments` (amount), `ToolDefinition.high_impact`, `ToolDefinition.category` (export means bulk) | |
| History | Earlier rows of the same `sequence_id`, ordered by `position` and `requested_at` | |
| Provenance | `ToolCall.provenance_labels` | |
| Policy context | `LabelledActionEvent.rule`, amount against the limits, `expected_outcome` of `HUMAN_REVIEW` | |
| Operational | `ToolCall.requested_at` (time of day), repeats within a sequence | |

### NFR-08: synthetic data only

| Check | Where to look | Result | Notes |
|---|---|---|---|
| A real email domain is rejected | Run the tests; see `test_rule_violations_are_rejected` | | |
| A phone number outside the fictional range is rejected | Same test | | |
| Unknown fields such as a government ID are rejected | `Entity` base class (`extra="forbid"`) | | |
| The examples contain nothing that looks real | `examples.json` | | |

## Findings

| # | Finding | Severity (low, medium, high) | Action |
|---|---|---|---|
| | | | |

## Decision

- [ ] Approved
- [ ] Approved with follow-ups (listed below and added to the board)
- [ ] Changes needed before approval

Follow-ups added to the board:
