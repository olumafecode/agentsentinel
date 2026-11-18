"""Tests for the gateway's outcome and audit contracts (US-18.2, US-19)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from sentinel_contracts import (
    ActionOutcome,
    AuditEventType,
    AuditRecord,
    Decision,
    ExecutionResult,
    ExecutionStatus,
    GovernanceDecision,
    ReasonCode,
)

CID = "3f2b8c1e-5a7d-4e9b-9c1a-2d4f6a8b0c1e"
WHEN = datetime(2027, 1, 15, 8, 0, tzinfo=UTC)


def decision(kind=Decision.ALLOW):
    allowed = kind is Decision.ALLOW
    return GovernanceDecision(
        correlation_id=CID,
        decision=kind,
        reason_codes=[ReasonCode.WITHIN_POLICY if allowed else ReasonCode.UNKNOWN_TOOL],
        summary="Allowed." if allowed else "Blocked.",
        execution_token="v1.claims.signature" if allowed else None,
        decided_at=WHEN,
    )


def execution(**changes):
    fields = {
        "status": ExecutionStatus.SUCCEEDED,
        "tool_name": "get_customer",
        "http_status": 200,
        "result": {"customer_id": "CUS-000123"},
        "completed_at": WHEN,
    }
    return ExecutionResult(**{**fields, **changes})


def test_an_allowed_outcome_carries_the_banks_result():
    outcome = ActionOutcome(decision=decision(), execution=execution())

    assert outcome.decision.permits_execution
    assert outcome.execution.result == {"customer_id": "CUS-000123"}


def test_a_blocked_outcome_has_no_execution():
    assert ActionOutcome(decision=decision(Decision.BLOCK)).execution is None


@pytest.mark.parametrize(
    ("kind", "with_execution"),
    [(Decision.ALLOW, False), (Decision.BLOCK, True)],
)
def test_execution_is_present_exactly_when_the_decision_is_allow(kind, with_execution):
    with pytest.raises(ValidationError, match="only for ALLOW"):
        ActionOutcome(
            decision=decision(kind), execution=execution() if with_execution else None
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"error": {"code": "x", "message": "y"}},
        {"status": ExecutionStatus.REJECTED, "http_status": 409},
        {"status": ExecutionStatus.FAILED, "error": {"code": "", "message": "y"}},
        {"http_status": 99},
        {"tool_name": "Get Customer"},
    ],
)
def test_an_execution_result_must_be_consistent(changes):
    with pytest.raises(ValidationError):
        execution(**changes)


def test_a_failed_execution_explains_why():
    failed = execution(
        status=ExecutionStatus.FAILED,
        http_status=None,
        result=None,
        error={"code": "bank_timeout", "message": "the bank did not answer in time"},
    )

    assert failed.error.code == "bank_timeout"


def test_an_outcome_survives_a_round_trip_through_json():
    outcome = ActionOutcome(decision=decision(), execution=execution())

    assert ActionOutcome.model_validate_json(outcome.model_dump_json()) == outcome


def test_an_audit_record_holds_one_step_of_an_action():
    record = AuditRecord(
        correlation_id=CID,
        event_type=AuditEventType.DECISION_MADE,
        actor="sentinel-gateway",
        decision=Decision.BLOCK,
        payload={"reason_codes": ["UNKNOWN_TOOL"], "checks": [{"check": "known_tool"}]},
        created_at=WHEN,
    )

    assert record.model_dump(mode="json")["event_type"] == "decision_made"


@pytest.mark.parametrize(
    "changes",
    [
        {"event_type": "action_teleported"},
        {"actor": "g"},
        {"payload": {"amount": float("nan")}},
        {"created_at": "2027-01-15T08:00:00"},
        {"event_hash": "0" * 64},
    ],
)
def test_an_audit_record_rejects_bad_values(changes):
    fields = {
        "correlation_id": CID,
        "event_type": "action_received",
        "actor": "sentinel-gateway",
        "payload": {},
        "created_at": WHEN,
    }
    with pytest.raises(ValidationError):
        AuditRecord(**{**fields, **changes})
