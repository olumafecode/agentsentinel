"""AT-03 Bulk export (US-02a.5, UC-05).

Vera asks for every customer record. Expected: BLOCK by the bank policy in OPA, the
bank API is not called, and the audit trail records the policy bundle version and
the rules that matched.
"""

import json
from pathlib import Path

import pytest

MANIFEST = Path(__file__).resolve().parents[2] / "policies" / "opa" / ".manifest"
BUNDLE_VERSION = json.loads(MANIFEST.read_text(encoding="utf-8"))["revision"]
TASKS = ["account_inquiry", "refund_request", "profile_update", "dispute"]


@pytest.mark.parametrize("task", TASKS)
def test_an_export_of_every_customer_is_blocked_and_never_reaches_the_bank(stack, task):
    response = stack.propose("export_customers", {}, task=task)

    assert response.status_code == 200
    outcome = response.json()
    decision = outcome["decision"]
    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"][0] == "POLICY_DENY"
    assert decision["summary"] == (
        "Exporting customer records in bulk is never allowed through an agent."
    )
    assert decision["policy_version"] == BUNDLE_VERSION
    assert decision["execution_token"] is None
    assert outcome["execution"] is None
    assert stack.bank_requests == []


def test_the_audit_trail_records_the_policy_version_and_the_rules_that_matched(stack):
    outcome = stack.propose("export_customers", {}).json()
    correlation_id = outcome["decision"]["correlation_id"]

    trail = stack.audit.for_correlation(correlation_id)

    assert [e.event_type for e in trail] == [
        "action_received",
        "decision_made",
        "action_stopped",
    ]
    decided = trail[1]
    assert decided.decision == "BLOCK"
    assert decided.policy_version == BUNDLE_VERSION
    checks = {c["check"]: c for c in decided.payload["checks"]}
    assert checks["bank_policy"]["decision"] == "BLOCK"
    assert checks["bank_policy"]["reason_codes"] == ["POLICY_DENY", "TOOL_NOT_ALLOWED"]
    assert checks["bank_policy"]["details"]["matched_rules"] == [
        "bulk_export",
        "tool_not_allowed_for_agent",
        "tool_not_allowed_for_task",
    ]
    assert trail[2].payload["reason_codes"] == ["POLICY_DENY", "TOOL_NOT_ALLOWED"]


def test_an_allowed_action_is_audited_with_the_policy_version_too(stack):
    outcome = stack.propose("get_transactions", {"customer_id": "CUS-000123"}).json()
    correlation_id = outcome["decision"]["correlation_id"]

    decided = stack.audit.for_correlation(correlation_id)[1]

    assert decided.decision == "ALLOW"
    assert decided.policy_version == BUNDLE_VERSION
    checks = {c["check"]: c for c in decided.payload["checks"]}
    assert checks["bank_policy"]["details"]["matched_rules"] == []
