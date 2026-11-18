"""The live contracts and the stored synthetic schema must describe the same data."""

import json
from pathlib import Path
from typing import get_args

import pytest

from data.synthetic import models
from sentinel_contracts import SessionClaims, actions, audit, identifiers

EXAMPLES = json.loads(
    (
        Path(__file__).resolve().parents[1] / "data" / "synthetic" / "examples.json"
    ).read_text(encoding="utf-8")
)


@pytest.mark.parametrize(
    ("contract_enum", "schema_enum"),
    [
        (actions.Decision, models.Decision),
        (actions.Provenance, models.Provenance),
        (actions.TaskType, models.TaskType),
        (audit.AuditEventType, models.AuditEventType),
    ],
)
def test_enumerations_have_the_same_values(contract_enum, schema_enum):
    assert {m.value for m in contract_enum} == {m.value for m in schema_enum}


@pytest.mark.parametrize(
    "name",
    [
        "CustomerId",
        "AccountId",
        "TransactionId",
        "AgentId",
        "SessionId",
        "ApprovalId",
        "CorrelationId",
        "SemVer",
        "ToolName",
        "EventId",
        "Sha256",
    ],
)
def test_identifier_formats_are_the_same(name):
    contract_pattern = get_args(getattr(identifiers, name))[1].pattern
    schema_pattern = get_args(getattr(models, name))[1].pattern
    assert contract_pattern == schema_pattern


def test_a_stored_tool_call_is_a_valid_live_request():
    request = actions.ProtectedActionRequest.model_validate(EXAMPLES["ToolCall"])
    stored = models.ToolCall.model_validate(EXAMPLES["ToolCall"])
    assert request.model_dump(mode="json") == stored.model_dump(mode="json")


def test_reason_codes_in_examples_are_known():
    assert set(EXAMPLES["AuditEvent"]["payload"]["reason_codes"]) <= {
        r.value for r in actions.ReasonCode
    }


def test_an_audit_record_is_an_audit_event_without_its_chain_fields():
    chain_fields = {"event_id", "previous_event_hash", "event_hash"}
    assert set(audit.AuditRecord.model_fields) == (
        set(models.AuditEvent.model_fields) - chain_fields
    )
    stored = models.AuditEvent.model_validate(EXAMPLES["AuditEvent"])
    record = audit.AuditRecord.model_validate(
        stored.model_dump(mode="json", exclude=chain_fields)
    )
    assert record.model_dump(mode="json") == stored.model_dump(
        mode="json", exclude=chain_fields
    )


def test_session_claims_carry_the_user_session_fields():
    session = models.UserSession.model_validate(EXAMPLES["UserSession"])
    claims = SessionClaims(
        session_id=session.session_id,
        customer_id=session.customer_id,
        agent_id=session.agent_id,
        task_type=session.task_type.value,
        channel=session.channel,
        issuer="veridane-identity",
        audience="sentinel-gateway",
        issued_at=int(session.started_at.timestamp()),
        expires_at=int(session.expires_at.timestamp()),
    )
    shared = {"session_id", "customer_id", "agent_id", "task_type", "channel"}
    assert shared <= set(models.UserSession.model_fields)
    assert claims.model_dump(mode="json", include=shared) == session.model_dump(
        mode="json", include=shared
    )
