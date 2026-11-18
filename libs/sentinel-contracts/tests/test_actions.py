"""Tests for the request and decision contracts (US-18.1)."""

import pytest
from pydantic import ValidationError

from sentinel_contracts import (
    Decision,
    GovernanceDecision,
    ProtectedActionRequest,
    Provenance,
    ReasonCode,
)

REQUEST = {
    "correlation_id": "3f2b8c1e-5a7d-4e9b-9c1a-2d4f6a8b0c1e",
    "session_id": "SES-00000042",
    "agent_id": "AGT-001",
    "customer_scope": "CUS-000123",
    "task_type": "refund_request",
    "tool_name": "issue_refund",
    "arguments": {
        "account_id": "ACC-00000123",
        "amount": "750.00",
        "original_transaction_id": "TXN-0000004567",
        "reason": "Duplicate charge",
    },
    "provenance_labels": {
        "account_id": "trusted_user_input",
        "amount": "trusted_user_input",
    },
    "requested_at": "2026-03-14T15:02:11Z",
}

DECISION = {
    "correlation_id": REQUEST["correlation_id"],
    "decision": "BLOCK",
    "reason_codes": ["OUTSIDE_CUSTOMER_SCOPE"],
    "summary": "Blocked: the account belongs to a different customer.",
    "decided_at": "2026-03-14T15:02:11Z",
}


def request(**changes):
    return ProtectedActionRequest.model_validate({**REQUEST, **changes})


def decision(**changes):
    return GovernanceDecision.model_validate({**DECISION, **changes})


def test_valid_request_is_accepted():
    parsed = request()
    assert parsed.tool_name == "issue_refund"
    assert parsed.provenance_labels["amount"] is Provenance.TRUSTED_USER_INPUT


def test_request_survives_a_json_round_trip():
    parsed = request()
    assert (
        ProtectedActionRequest.model_validate_json(parsed.model_dump_json()) == parsed
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"correlation_id": "not-a-uuid"},
        {"session_id": "42"},
        {"agent_id": "vera"},
        {"customer_scope": "CUS-123"},
        {"task_type": "wire_transfer"},
        {"tool_name": "Issue-Refund"},
        {"arguments": {"Account ID": "ACC-00000123"}, "provenance_labels": {}},
        {"provenance_labels": {"iban": "untrusted_content"}},
        {"provenance_labels": {"amount": "from_email"}},
        {"requested_at": "2026-03-14T15:02:11"},
        {"role": "admin"},
    ],
)
def test_invalid_request_is_rejected(changes):
    with pytest.raises(ValidationError):
        request(**changes)


def test_request_limits_the_number_of_arguments():
    arguments = {f"arg_{i}": i for i in range(33)}
    with pytest.raises(ValidationError):
        request(arguments=arguments, provenance_labels={})


def test_request_cannot_be_changed_after_creation():
    parsed = request()
    with pytest.raises(ValidationError):
        parsed.tool_name = "export_customers"


def test_block_decision_is_accepted():
    parsed = decision()
    assert parsed.decision is Decision.BLOCK
    assert parsed.reason_codes == [ReasonCode.OUTSIDE_CUSTOMER_SCOPE]
    assert not parsed.permits_execution


def test_allow_decision_carries_a_token():
    parsed = decision(
        decision="ALLOW", reason_codes=["WITHIN_POLICY"], execution_token="v1.a.b"
    )
    assert parsed.permits_execution


def test_allow_after_human_approval_may_name_the_approval():
    parsed = decision(
        decision="ALLOW",
        reason_codes=["APPROVED_BY_HUMAN"],
        execution_token="v1.a.b",
        approval_id="APR-000007",
    )
    assert parsed.approval_id == "APR-000007"


@pytest.mark.parametrize(
    "changes",
    [
        {"decision": "ALLOW"},
        {"decision": "BLOCK", "execution_token": "v1.a.b"},
        {"decision": "QUARANTINE", "execution_token": "v1.a.b"},
        {
            "decision": "HUMAN_REVIEW",
            "execution_token": "v1.a.b",
            "approval_id": "APR-000001",
        },
        {"decision": "HUMAN_REVIEW"},
        {"reason_codes": []},
        {"reason_codes": ["NOT_A_REASON"]},
        {"reason_codes": ["POLICY_DENY", "POLICY_DENY"]},
        {"summary": ""},
        {"policy_version": "v1"},
        {"approval_id": "7"},
        {"decided_at": "yesterday"},
    ],
)
def test_inconsistent_decision_is_rejected(changes):
    with pytest.raises(ValidationError):
        decision(**changes)


def test_decision_survives_a_json_round_trip():
    parsed = decision(
        decision="HUMAN_REVIEW",
        reason_codes=["REFUND_OVER_LIMIT"],
        approval_id="APR-000007",
    )
    assert GovernanceDecision.model_validate_json(parsed.model_dump_json()) == parsed
