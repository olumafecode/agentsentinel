"""The gateway signs a single-use token for each allowed call, and the bank enforces it (US-18.4, US-18.6)."""

import pytest

from sentinel_contracts import TOKEN_HEADER, verify_token
from sentinel_gateway.config import BANK_AUDIENCE


@pytest.fixture
def allowed_refund(evaluate, refund, refund_session):
    """Evaluate a refund the gateway allows; return the request body and the decision."""
    body = refund()
    response = evaluate(body, session=refund_session)
    decision = response.json()["decision"]
    assert decision["decision"] == "ALLOW"
    return body, decision


def test_the_token_is_bound_to_this_exact_call(allowed_refund, settings, clock):
    body, decision = allowed_refund

    claims = verify_token(
        decision["execution_token"],
        key=settings.execution_token_key,
        audience=BANK_AUDIENCE,
        tool_name="issue_refund",
        arguments=body["arguments"],
        now=clock(),
    )

    assert claims.correlation_id == body["correlation_id"]
    assert claims.customer_scope == "CUS-000123"
    assert claims.expires_at - claims.issued_at == 60


def test_a_replayed_token_is_rejected_by_the_bank(allowed_refund, bank, refunds_for):
    body, decision = allowed_refund

    replay = bank.post(
        "/v1/tools/issue_refund",
        json=body["arguments"],
        headers={TOKEN_HEADER: decision["execution_token"]},
    )

    assert replay.status_code == 403
    assert replay.json()["error"]["code"] == "token_replayed"
    assert len(refunds_for("TXN-0000004568")) == 1


@pytest.mark.parametrize(
    ("tool_name", "arguments", "code"),
    [
        pytest.param(
            "issue_refund",
            {
                "account_id": "ACC-99000017",
                "amount": "120.00",
                "original_transaction_id": "TXN-0000004568",
                "reason": "Duplicate charge",
            },
            "token_arguments_mismatch",
            id="refund redirected to another account",
        ),
        pytest.param(
            "export_customers",
            {},
            "token_tool_mismatch",
            id="token reused for another tool",
        ),
    ],
)
def test_a_token_cannot_be_reused_for_a_different_call(
    evaluate,
    refund,
    refund_session,
    unforwarded_gateway,
    bank,
    refunds_for,
    tool_name,
    arguments,
    code,
):
    body = refund()
    decision = evaluate(
        body, session=refund_session, client=unforwarded_gateway
    ).json()["decision"]

    response = bank.post(
        f"/v1/tools/{tool_name}",
        json=arguments,
        headers={TOKEN_HEADER: decision["execution_token"]},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == code
    assert refunds_for("TXN-0000004568") == []


def test_an_expired_token_is_rejected(
    evaluate, refund, refund_session, unforwarded_gateway, bank, clock
):
    body = refund()
    decision = evaluate(
        body, session=refund_session, client=unforwarded_gateway
    ).json()["decision"]
    clock.advance(61)

    response = bank.post(
        "/v1/tools/issue_refund",
        json=body["arguments"],
        headers={TOKEN_HEADER: decision["execution_token"]},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "token_expired"


def test_the_bank_refuses_a_call_that_did_not_come_through_the_gateway(bank, refund):
    response = bank.post("/v1/tools/issue_refund", json=refund()["arguments"])

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "missing_token"


def test_a_blocked_decision_carries_no_token(evaluate, action):
    decision = evaluate(action(), session=None).json()["decision"]

    assert decision["decision"] == "BLOCK"
    assert decision["execution_token"] is None
