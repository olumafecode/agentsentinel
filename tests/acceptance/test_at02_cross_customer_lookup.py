"""AT-02 Cross-customer lookup (US-01.4, UC-04).

Customer A's session asks for Customer B's records. Expected: BLOCK, the bank API is
not called at all, and a complete audit trail for the correlation ID.
"""

import pytest

CUSTOMER_A = "CUS-000123"
CUSTOMER_B = "CUS-000456"

CROSS_CUSTOMER = [
    pytest.param(
        "get_transactions",
        {"customer_id": CUSTOMER_B, "limit": 10},
        {},
        "OUTSIDE_CUSTOMER_SCOPE",
        id="B's transactions",
    ),
    pytest.param(
        "get_customer",
        {"customer_id": CUSTOMER_B},
        {},
        "OUTSIDE_CUSTOMER_SCOPE",
        id="B's profile",
    ),
    pytest.param(
        "get_transactions",
        {"customer_id": CUSTOMER_B, "limit": 10},
        {"customer_scope": CUSTOMER_B},
        "IDENTITY_MISMATCH",
        id="claiming B's scope in A's session",
    ),
]


@pytest.mark.parametrize(("tool_name", "arguments", "change", "reason"), CROSS_CUSTOMER)
def test_customer_b_records_are_blocked_and_the_bank_is_never_called(
    stack, tool_name, arguments, change, reason
):
    response = stack.propose(tool_name, arguments, customer=CUSTOMER_A, **change)

    assert response.status_code == 200
    outcome = response.json()
    assert outcome["decision"]["decision"] == "BLOCK"
    assert outcome["decision"]["reason_codes"] == [reason]
    assert outcome["decision"]["execution_token"] is None
    assert outcome["execution"] is None
    assert stack.bank_requests == []


@pytest.mark.parametrize(("tool_name", "arguments", "change", "reason"), CROSS_CUSTOMER)
def test_the_blocked_lookup_leaves_a_complete_audit_trail(
    stack, tool_name, arguments, change, reason
):
    outcome = stack.propose(tool_name, arguments, customer=CUSTOMER_A, **change).json()
    correlation_id = outcome["decision"]["correlation_id"]

    trail = stack.audit.for_correlation(correlation_id)

    assert [e.event_type for e in trail] == [
        "action_received",
        "decision_made",
        "action_stopped",
    ]
    received, decided, stopped = trail
    assert received.payload["request"]["arguments"] == arguments
    assert received.payload["session"]["customer_id"] == CUSTOMER_A
    assert decided.decision == "BLOCK"
    assert decided.payload["reason_codes"] == [reason]
    assert stopped.decision == "BLOCK"
    assert stopped.payload == {"reason_codes": [reason]}


def test_the_same_request_in_b_own_session_is_allowed(stack):
    outcome = stack.propose(
        "get_transactions",
        {"customer_id": CUSTOMER_B, "limit": 10},
        customer=CUSTOMER_B,
    ).json()

    assert outcome["decision"]["decision"] == "ALLOW"
    assert len(stack.bank_requests) == 1
