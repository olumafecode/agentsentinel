"""What Vera says about each outcome."""

from datetime import UTC, datetime

import pytest

from banking_agent import replies
from sentinel_contracts import (
    ActionOutcome,
    Decision,
    ExecutionResult,
    GovernanceDecision,
)

WHEN = datetime(2027, 1, 15, 8, tzinfo=UTC)


def allowed(tool_name, *, result=None, status="succeeded", error=None):
    return ActionOutcome(
        decision=GovernanceDecision(
            correlation_id="3f2b8c1e-5a7d-4e9b-9c1a-2d4f6a8b0c1e",
            decision=Decision.ALLOW,
            reason_codes=["WITHIN_POLICY"],
            summary="Allowed.",
            execution_token="v1.token.signature",
            decided_at=WHEN,
        ),
        execution=ExecutionResult(
            status=status,
            tool_name=tool_name,
            result=result,
            error=error,
            completed_at=WHEN,
        ),
    )


@pytest.mark.parametrize(
    ("tool_name", "result", "text"),
    [
        ("get_transactions", [{}], "Here are your 1 most recent transaction."),
        ("get_accounts", [{}, {}], "You have 2 accounts with us."),
        (
            "update_address",
            {"address": "1 New Street"},
            "Your mailing address is now 1 New Street.",
        ),
        (
            "issue_refund",
            {"amount": "120.00", "account_id": "ACC-00000123"},
            "Your refund of 120.00 USD has been issued to ACC-00000123.",
        ),
        (
            "close_dispute",
            {"dispute_id": "DSP-000001"},
            "Dispute DSP-000001 is now closed.",
        ),
        ("get_customer", {"unexpected": True}, "Done."),
    ],
)
def test_a_successful_call_is_described(tool_name, result, text):
    assert replies.describe(tool_name, allowed(tool_name, result=result)) == text


def test_a_bank_refusal_is_passed_on():
    outcome = allowed(
        "issue_refund",
        status="rejected",
        error={
            "code": "refund_exceeds_original",
            "message": "only 0.00 is left to refund.",
        },
    )

    assert replies.describe("issue_refund", outcome) == (
        "The bank couldn't complete that: only 0.00 is left to refund."
    )


def test_an_unconfirmed_call_must_not_be_repeated():
    outcome = allowed(
        "issue_refund",
        status="failed",
        error={"code": "bank_timeout", "message": "the bank did not answer in time"},
    )

    assert "don't repeat it" in replies.describe("issue_refund", outcome)
