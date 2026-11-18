"""Scripted fixtures for UC-01 to UC-07 and the checks the runner makes (US-17.2)."""

import pytest
from pydantic import ValidationError

from banking_agent.identity import IdentityStandIn
from banking_agent.scenarios import Expectation, Scenario, load_scenarios, run_scenario
from sentinel_contracts import Decision, load_key, verify_session_token

SESSION_KEY = load_key("session-key-for-vera-tests-0123456789abcdef")
SCENARIOS = {scenario.id: scenario for scenario in load_scenarios()}


@pytest.fixture
def identity():
    return IdentityStandIn(SESSION_KEY, clock=lambda: 1_800_000_000.0)


def test_there_is_a_scenario_for_each_use_case_from_uc01_to_uc07():
    assert list(SCENARIOS) == [f"UC-0{n}" for n in range(1, 8)]


def test_scenarios_wait_only_on_the_stories_that_deliver_their_controls():
    pending = {s.id: s.pending_on for s in SCENARIOS.values() if s.status == "pending"}

    assert pending == {"UC-03": "US-03", "UC-06": "US-04", "UC-07": "US-05"}


def test_the_identity_stand_in_signs_a_session_for_the_customer(identity):
    session = identity.sign_in("CUS-000123", "refund_request", agent_id="AGT-001")

    claims = verify_session_token(session.token, key=SESSION_KEY, now=1_800_000_000.0)
    assert claims.customer_id == session.customer_id == "CUS-000123"
    assert claims.session_id == session.session_id
    assert claims.task_type == session.task_type == "refund_request"
    assert claims.agent_id == "AGT-001"
    assert session.token not in repr(session)


def test_a_scenario_passes_when_every_decision_matches(vera, fake_gateway, identity):
    fake_gateway.decisions["get_transactions"] = [Decision.BLOCK, Decision.ALLOW]

    result = run_scenario(SCENARIOS["UC-04"], vera, identity)

    assert result.status == "passed"
    assert result.problems == []
    assert [r.proposal.decision for r in result.calls] == [
        Decision.BLOCK,
        Decision.ALLOW,
    ]


def test_a_wrong_decision_fails_the_scenario(vera, fake_gateway, identity):
    result = run_scenario(SCENARIOS["UC-04"], vera, identity)

    assert result.status == "failed"
    assert result.problems == [
        "turn 1, get_transactions: expected BLOCK, got ALLOW",
        (
            "turn 1, get_transactions: expected reason codes OUTSIDE_CUSTOMER_SCOPE, "
            "got WITHIN_POLICY"
        ),
    ]


def test_a_refused_call_that_vera_proposes_again_fails_the_scenario(
    vera, fake_gateway, identity
):
    fake_gateway.decisions["issue_refund"] = Decision.HUMAN_REVIEW

    result = run_scenario(SCENARIOS["UC-02"], vera, identity)

    assert "turn 1, issue_refund: expected BLOCK, got HUMAN_REVIEW" in result.problems
    assert result.calls[1].proposal is None
    assert result.calls[1].problems == ()


def test_a_call_vera_should_not_propose_is_checked(vera, fake_gateway, identity):
    fake_gateway.decisions["issue_refund"] = Decision.BLOCK

    result = run_scenario(SCENARIOS["UC-02"], vera, identity)

    assert result.status == "passed"
    assert fake_gateway.tools_called == ["issue_refund"]


def test_a_pending_scenario_reports_but_never_fails(vera, fake_gateway, identity):
    result = run_scenario(SCENARIOS["UC-03"], vera, identity)

    assert result.problems
    assert result.status == "pending"


@pytest.mark.parametrize(
    "fields",
    [
        {"proposed": True},
        {"proposed": False, "decision": "BLOCK"},
        {"proposed": False, "reason_codes": ["POLICY_DENY"]},
    ],
)
def test_an_expectation_must_be_consistent(fields):
    with pytest.raises(ValidationError):
        Expectation(**fields)


@pytest.mark.parametrize(
    "change",
    [
        {"status": "pending"},
        {"pending_on": "US-03"},
        {"id": "UC-1"},
        {"turns": []},
    ],
)
def test_a_malformed_scenario_is_rejected(change):
    data = SCENARIOS["UC-01"].model_dump(mode="json", exclude_none=True)

    with pytest.raises(ValidationError):
        Scenario.model_validate({**data, **change})


def test_a_scripted_call_cannot_label_an_argument_it_does_not_have():
    data = SCENARIOS["UC-05"].model_dump(mode="json", exclude_none=True)
    data["turns"][0]["calls"][0]["provenance"] = {"customer_id": "system"}

    with pytest.raises(ValidationError, match="provenance"):
        Scenario.model_validate(data)
