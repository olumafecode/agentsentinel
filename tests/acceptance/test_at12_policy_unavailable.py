"""AT-12 Gateway dependency failure, for the bank policy (US-02a).

OPA is unavailable during a sensitive call. Expected: the gateway fails closed, the
bank is not called, the fault is logged, and the action is still fully audited. The
risk engine half of AT-12 comes with US-04.
"""

import logging
import socket

import pytest


@pytest.fixture
def stack_without_opa(make_stack):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    # Nothing listens on the port once the socket is closed.
    return make_stack(opa_url=f"http://127.0.0.1:{port}")


REFUND = {
    "account_id": "ACC-00000123",
    "amount": "120.00",
    "original_transaction_id": "TXN-0000004568",
    "reason": "Duplicate charge",
}


def test_a_refund_is_blocked_while_the_policy_cannot_be_reached(
    stack_without_opa, caplog
):
    with caplog.at_level(logging.ERROR, logger="sentinel_gateway.orchestrator"):
        response = stack_without_opa.propose(
            "issue_refund", REFUND, task="refund_request"
        )

    assert response.status_code == 200
    outcome = response.json()
    assert outcome["decision"]["decision"] == "BLOCK"
    assert outcome["decision"]["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
    assert outcome["decision"]["policy_version"] is None
    assert outcome["execution"] is None
    assert stack_without_opa.bank_requests == []
    assert "check bank_policy failed" in caplog.text

    trail = stack_without_opa.audit.for_correlation(
        outcome["decision"]["correlation_id"]
    )
    assert [e.event_type for e in trail] == [
        "action_received",
        "decision_made",
        "action_stopped",
    ]
    checks = {c["check"]: c for c in trail[1].payload["checks"]}
    assert checks["bank_policy"]["details"] == {"error": "PolicyUnavailable"}


def test_the_gateway_reports_not_ready_while_the_policy_is_down(stack_without_opa):
    response = stack_without_opa.gateway.get("/readyz")

    assert response.status_code == 503
    assert response.json()["policy"] == "unavailable"
    assert response.json()["audit"] == "ready"
