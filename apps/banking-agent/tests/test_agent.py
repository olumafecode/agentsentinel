"""Vera's agent loop: proposals, refusals and determinism (US-17.4)."""

import httpx2
import pytest

from banking_agent import replies
from banking_agent.planning import PlannedCall, ScriptedPlanner
from banking_agent.scenarios import load_scenarios
from sentinel_contracts import Decision

LOOKUP = PlannedCall(
    tool_name="get_transactions",
    arguments={"customer_id": "CUS-000123", "limit": 5},
    provenance={"customer_id": "system"},
)
PROFILE = PlannedCall(tool_name="get_customer", arguments={"customer_id": "CUS-000123"})
REFUND = PlannedCall(
    tool_name="issue_refund",
    arguments={
        "account_id": "ACC-99000017",
        "amount": "120.00",
        "original_transaction_id": "TXN-0000004568",
        "reason": "Duplicate charge",
    },
    provenance={"account_id": "untrusted_content"},
)


def talk(vera, session, *turns):
    messages = [f"message {n}" for n in range(len(turns))]
    return vera.converse(session, messages, ScriptedPlanner(turns))


def test_each_call_becomes_a_request_bound_to_the_session(vera, session, fake_gateway):
    talk(vera, session, [LOOKUP])

    [(_, body)] = fake_gateway.requests
    assert body["session_id"] == "SES-00000042"
    assert body["agent_id"] == "AGT-001"
    assert body["customer_scope"] == "CUS-000123"
    assert body["task_type"] == "account_inquiry"
    assert body["tool_name"] == "get_transactions"
    assert body["arguments"] == {"customer_id": "CUS-000123", "limit": 5}
    assert body["provenance_labels"] == {"customer_id": "system"}
    assert body["requested_at"] == "2027-01-15T08:00:00Z"


def test_allowed_calls_are_reported_and_the_turn_goes_on(vera, session, fake_gateway):
    conversation = talk(vera, session, [LOOKUP, PROFILE])

    [turn] = conversation.turns
    assert [p.decision for p in turn.proposals] == [Decision.ALLOW, Decision.ALLOW]
    assert turn.reply == (
        "Here are your 2 most recent transactions. I have your profile, Avery Stone."
    )
    assert not conversation.ended


def test_a_blocked_call_is_refused_out_loud_and_ends_the_turn(
    vera, session, fake_gateway
):
    fake_gateway.decisions["issue_refund"] = Decision.BLOCK

    conversation = talk(vera, session, [REFUND, LOOKUP])

    [turn] = conversation.turns
    assert turn.reply == "I'm sorry, I can't do that. Decided BLOCK."
    assert turn.not_proposed == [LOOKUP]
    assert fake_gateway.tools_called == ["issue_refund"]


def test_vera_never_retries_a_refused_call(vera, session, fake_gateway):
    fake_gateway.decisions["issue_refund"] = Decision.BLOCK

    conversation = talk(vera, session, [REFUND], [REFUND, LOOKUP], [REFUND])

    assert fake_gateway.tools_called == ["issue_refund", "get_transactions"]
    assert conversation.turns[1].not_proposed == [REFUND]
    assert conversation.turns[1].reply.startswith(replies.ALREADY_REFUSED)
    assert conversation.turns[2].reply == replies.ALREADY_REFUSED


def test_the_same_tool_with_other_arguments_is_a_new_call(vera, session, fake_gateway):
    fake_gateway.decisions["issue_refund"] = Decision.BLOCK
    own_account = REFUND.model_copy(
        update={"arguments": {**REFUND.arguments, "account_id": "ACC-00000123"}}
    )

    talk(vera, session, [REFUND], [own_account])

    assert fake_gateway.tools_called == ["issue_refund", "issue_refund"]


def test_a_held_call_waits_and_is_not_sent_twice(vera, session, fake_gateway):
    fake_gateway.decisions["issue_refund"] = Decision.HUMAN_REVIEW

    conversation = talk(vera, session, [REFUND, LOOKUP], [REFUND])

    assert "request APR-000007" in conversation.turns[0].reply
    assert conversation.turns[0].not_proposed == [LOOKUP]
    assert conversation.turns[1].reply == replies.ALREADY_HELD
    assert fake_gateway.tools_called == ["issue_refund"]


def test_quarantine_ends_the_conversation(vera, session, fake_gateway):
    fake_gateway.decisions["get_customer"] = Decision.QUARANTINE

    conversation = talk(vera, session, [PROFILE], [LOOKUP])

    assert conversation.ended
    assert (
        conversation.turns[0].reply
        == "I'm sorry, I can't continue. Decided QUARANTINE."
    )
    assert conversation.turns[1].not_proposed == [LOOKUP]
    assert fake_gateway.tools_called == ["get_customer"]


def test_an_unreachable_gateway_means_nothing_was_done(vera, session, fake_gateway):
    fake_gateway.decisions["get_transactions"] = [httpx2.ConnectError("refused")]

    conversation = talk(vera, session, [LOOKUP, PROFILE], [PROFILE])

    first, second = conversation.turns
    assert first.reply == replies.UNAVAILABLE
    assert first.proposals[0].error == "gateway_unreachable"
    assert first.not_proposed == [PROFILE]
    assert second.proposals[0].decision is Decision.ALLOW
    assert not conversation.ended


def test_a_gateway_that_refuses_vera_ends_the_conversation(vera, session, fake_gateway):
    fake_gateway.decisions["get_transactions"] = [401]

    conversation = talk(vera, session, [LOOKUP], [PROFILE])

    assert conversation.turns[0].reply == replies.DISCONNECTED
    assert conversation.ended
    assert conversation.turns[1].not_proposed == [PROFILE]


def test_a_turn_without_calls_still_gets_a_reply(vera, session):
    conversation = talk(vera, session, [])

    assert conversation.turns[0].reply == replies.NOTHING_TO_DO


@pytest.mark.parametrize("scenario", load_scenarios(), ids=lambda s: s.id)
def test_a_scripted_scenario_proposes_the_same_calls_every_time(
    vera, session, fake_gateway, scenario
):
    first = vera.converse(session, scenario.messages(), scenario.planner())
    second = vera.converse(session, scenario.messages(), scenario.planner())

    assert first.proposed_calls() == second.proposed_calls()
    assert len(first.proposed_calls()) >= 1
    assert set(first.correlation_ids()).isdisjoint(second.correlation_ids())
