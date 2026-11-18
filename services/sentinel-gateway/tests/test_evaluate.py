"""The evaluate endpoint: context binding, deny by default and what reaches the bank (US-18.2)."""

import uuid
from datetime import UTC, datetime

import pytest

from sentinel_contracts import SESSION_HEADER, issue_session_token, load_key
from sentinel_gateway.registry import AgentStatus


def decision_of(response):
    assert response.status_code == 200, response.text
    return response.json()["decision"]


def test_an_allowed_lookup_runs_at_the_bank_and_returns_its_result(
    evaluate, action, bank
):
    body = action()
    response = evaluate(body)

    outcome = response.json()
    assert outcome["decision"]["decision"] == "ALLOW"
    assert outcome["decision"]["reason_codes"] == ["WITHIN_POLICY"]
    assert outcome["decision"]["correlation_id"] == body["correlation_id"]
    assert outcome["execution"]["status"] == "succeeded"
    assert outcome["execution"]["http_status"] == 200
    assert len(outcome["execution"]["result"]) == 2
    assert response.headers["X-Correlation-ID"] == body["correlation_id"]
    assert "X-Idempotent-Replay" not in response.headers
    assert len(bank.calls) == 1


def test_an_allowed_refund_changes_the_bank(
    evaluate, refund, refund_session, refunds_for
):
    response = evaluate(refund(), session=refund_session)

    outcome = response.json()
    assert outcome["decision"]["decision"] == "ALLOW"
    assert outcome["execution"]["status"] == "succeeded"
    assert outcome["execution"]["result"]["amount"] == "120.00"
    assert len(refunds_for("TXN-0000004568")) == 1


@pytest.mark.parametrize(
    ("session", "reason"),
    [
        pytest.param(None, "MISSING_CONTEXT", id="no session token"),
        pytest.param("not-a-token", "IDENTITY_MISMATCH", id="garbage"),
        pytest.param(
            issue_session_token(
                key=load_key("a-key-the-gateway-does-not-trust-0123456789"),
                session_id="SES-00000042",
                customer_id="CUS-000123",
                agent_id="AGT-001",
                task_type="account_inquiry",
            ),
            "IDENTITY_MISMATCH",
            id="signed with another key",
        ),
    ],
)
def test_an_action_without_a_valid_session_is_blocked(
    evaluate, action, bank, session, reason
):
    decision = decision_of(evaluate(action(), session=session))

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == [reason]
    assert decision["execution_token"] is None
    assert bank.calls == []


def test_an_expired_session_is_missing_context(
    evaluate, action, session_token, clock, bank
):
    token = session_token()
    clock.advance(31 * 60)

    decision = decision_of(evaluate(action(), session=token))

    assert decision["reason_codes"] == ["MISSING_CONTEXT"]
    assert bank.calls == []


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"customer_scope": "CUS-000456"}, "customer_scope"),
        ({"session_id": "SES-00000099"}, "session_id"),
        ({"task_type": "refund_request"}, "task_type"),
    ],
)
def test_an_action_that_does_not_match_its_session_is_blocked(
    evaluate, action, audit, bank, change, field
):
    body = action(**change)
    decision = decision_of(evaluate(body))

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["IDENTITY_MISMATCH"]
    assert field in decision["summary"]
    checks = audit.for_correlation(body["correlation_id"])[1].payload["checks"]
    assert checks[0]["details"] == {"fields": [field]}
    assert bank.calls == []


def test_an_agent_cannot_act_under_another_agents_id(
    evaluate, action, session_token, bank
):
    body = action(agent_id="AGT-001")
    atlas_session = session_token(agent_id="AGT-002")

    decision = decision_of(evaluate(body, agent="AGT-002", session=atlas_session))

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["IDENTITY_MISMATCH"]
    assert bank.calls == []


def test_an_agent_cannot_use_another_agents_session(
    evaluate, action, session_token, bank
):
    body = action(agent_id="AGT-002")

    decision = decision_of(evaluate(body, agent="AGT-002", session=session_token()))

    assert decision["reason_codes"] == ["IDENTITY_MISMATCH"]
    assert bank.calls == []


def test_an_unknown_tool_is_blocked(evaluate, action, bank):
    body = action(tool_name="wire_transfer", arguments={}, provenance_labels={})
    decision = decision_of(evaluate(body))

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["UNKNOWN_TOOL"]
    assert "wire_transfer" in decision["summary"]
    assert bank.calls == []


@pytest.mark.parametrize(
    ("change", "reasons"),
    [
        pytest.param({"customer_scope": None}, ["MISSING_CONTEXT"], id="no customer"),
        pytest.param({"task_type": "small_talk"}, ["MISSING_CONTEXT"], id="bad task"),
        pytest.param({"tool_name": "Export-All"}, ["UNKNOWN_TOOL"], id="bad tool name"),
        pytest.param(
            {"provenance_labels": {"amount": "system"}},
            ["INVALID_ARGUMENTS"],
            id="label for a missing argument",
        ),
        pytest.param({"extra": 1}, ["MISSING_CONTEXT"], id="unknown field"),
        pytest.param(
            {"requested_at": "yesterday", "arguments": []},
            ["MISSING_CONTEXT", "INVALID_ARGUMENTS"],
            id="several problems",
        ),
    ],
)
def test_a_malformed_action_is_still_decided_and_blocked(
    evaluate, action, bank, change, reasons
):
    body = action(**change)
    decision = decision_of(evaluate(body))

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == reasons
    assert decision["correlation_id"] == body["correlation_id"]
    assert bank.calls == []


@pytest.mark.parametrize("correlation_id", [None, "not-a-uuid", 42, str(uuid.uuid1())])
def test_an_action_without_a_valid_correlation_id_gets_one_and_is_blocked(
    evaluate, action, audit, bank, correlation_id
):
    body = action(correlation_id=correlation_id)
    response = evaluate(body)
    decision = decision_of(response)

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["MISSING_CONTEXT"]
    assigned = decision["correlation_id"]
    assert uuid.UUID(assigned).version == 4
    assert assigned != correlation_id
    assert response.headers["X-Correlation-ID"] == assigned
    assert [e.event_type for e in audit.for_correlation(assigned)] == [
        "action_received",
        "decision_made",
        "action_stopped",
    ]
    assert bank.calls == []


@pytest.mark.parametrize(
    ("minutes", "allowed"), [(-6, False), (-4, True), (0.4, True), (1, False)]
)
def test_only_freshly_proposed_actions_are_accepted(
    evaluate, action, clock, minutes, allowed
):
    requested_at = datetime.fromtimestamp(clock() + minutes * 60, tz=UTC).isoformat()
    decision = decision_of(evaluate(action(requested_at=requested_at)))

    assert (decision["decision"] == "ALLOW") is allowed
    if not allowed:
        assert decision["reason_codes"] == ["STALE_REQUEST"]


def test_a_quarantined_agent_gets_quarantine_and_nothing_runs(
    evaluate, action, agents, bank
):
    agents.set_status("AGT-001", AgentStatus.QUARANTINED)

    decision = decision_of(evaluate(action()))

    assert decision["decision"] == "QUARANTINE"
    assert decision["reason_codes"] == ["AGENT_QUARANTINED"]
    assert bank.calls == []


def test_quarantine_outranks_other_context_problems(evaluate, action, agents, bank):
    agents.set_status("AGT-001", AgentStatus.QUARANTINED)

    decision = decision_of(evaluate(action(tool_name="wire_transfer"), session=None))

    assert decision["decision"] == "QUARANTINE"
    assert decision["reason_codes"] == [
        "AGENT_QUARANTINED",
        "MISSING_CONTEXT",
        "UNKNOWN_TOOL",
    ]
    assert bank.calls == []


def test_a_disabled_agent_is_blocked(evaluate, action, agents, bank):
    agents.set_status("AGT-001", AgentStatus.DISABLED)

    decision = decision_of(evaluate(action()))

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["AGENT_DISABLED"]
    assert bank.calls == []


@pytest.mark.parametrize(
    ("headers", "code"),
    [
        ({}, "missing_agent_key"),
        ({"Authorization": "Basic dmVyYTpzZWNyZXQ="}, "missing_agent_key"),
        ({"Authorization": "Bearer "}, "missing_agent_key"),
        (
            {"Authorization": "Bearer not-the-right-key-0123456789abcdefgh"},
            "invalid_agent_key",
        ),
    ],
)
def test_a_caller_without_a_valid_agent_key_is_refused(
    gateway, action, audit, headers, code
):
    response = gateway.post("/v1/actions/evaluate", json=action(), headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == code
    assert audit.events == []


def test_the_agent_key_scheme_is_case_insensitive(
    gateway, action, session_token, agent_keys
):
    response = gateway.post(
        "/v1/actions/evaluate",
        json=action(),
        headers={
            "Authorization": f"bearer {agent_keys['AGT-001']}",
            SESSION_HEADER: session_token(),
        },
    )

    assert decision_of(response)["decision"] == "ALLOW"


@pytest.mark.parametrize(
    ("content", "status", "code"),
    [
        (b"{not json", 400, "invalid_json"),
        (b"[1, 2, 3]", 400, "invalid_json"),
        (b'{"amount": NaN}', 400, "invalid_json"),
        (b"[" * 100_000, 413, "body_too_large"),
        (b"[" * 60_000, 400, "invalid_json"),
    ],
)
def test_a_body_that_is_not_a_json_object_is_refused(
    gateway, audit, agent_keys, content, status, code
):
    response = gateway.post(
        "/v1/actions/evaluate",
        content=content,
        headers={
            "Authorization": f"Bearer {agent_keys['AGT-001']}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert audit.events == []
