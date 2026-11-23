"""AT-01 Normal transaction lookup (US-01.3, UC-01).

Customer A asks for their own transactions. Expected: ALLOW, the correct data, and a
complete audit trail for the correlation ID.
"""

import pytest

from demo_bank_api.store import BankStore

CUSTOMER_A = "CUS-000123"
SEEDED = BankStore()


def test_customer_a_gets_their_own_transactions(stack):
    response = stack.propose(
        "get_transactions", {"customer_id": CUSTOMER_A, "limit": 10}
    )

    assert response.status_code == 200
    outcome = response.json()
    assert outcome["decision"]["decision"] == "ALLOW"
    assert outcome["decision"]["reason_codes"] == ["WITHIN_POLICY"]
    assert outcome["execution"]["status"] == "succeeded"

    expected = [
        t.model_dump(mode="json") for t in SEEDED.list_transactions(CUSTOMER_A, 10)
    ]
    own_accounts = {a.account_id for a in SEEDED.list_accounts(CUSTOMER_A)}
    assert outcome["execution"]["result"] == expected
    assert {t["account_id"] for t in outcome["execution"]["result"]} <= own_accounts
    assert [r.url.path for r in stack.bank_requests] == ["/v1/tools/get_transactions"]


def test_customer_a_gets_their_own_profile(stack):
    outcome = stack.propose("get_customer", {"customer_id": CUSTOMER_A}).json()

    assert outcome["decision"]["decision"] == "ALLOW"
    assert outcome["execution"]["result"]["full_name"] == "Avery Stone"


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("get_transactions", {"customer_id": CUSTOMER_A, "limit": 10}),
        ("get_customer", {"customer_id": CUSTOMER_A}),
    ],
)
def test_the_lookup_leaves_a_complete_audit_trail(stack, tool_name, arguments):
    outcome = stack.propose(tool_name, arguments).json()
    correlation_id = outcome["decision"]["correlation_id"]

    trail = stack.audit.for_correlation(correlation_id)

    assert [e.event_type for e in trail] == [
        "action_received",
        "decision_made",
        "action_executed",
    ]
    received, decided, executed = trail
    assert received.payload["request"]["tool_name"] == tool_name
    assert received.payload["session"]["customer_id"] == CUSTOMER_A
    assert decided.decision == "ALLOW"
    assert decided.payload["reason_codes"] == ["WITHIN_POLICY"]
    assert {c["check"]: c["decision"] for c in decided.payload["checks"]} == {
        "context_binding": None,
        "agent_status": None,
        "request_freshness": None,
        "known_tool": None,
        "bank_policy": None,
        "customer_scope": None,
    }
    assert executed.payload["status"] == "succeeded"
    assert all(e.actor == "sentinel-gateway" for e in trail)
    assert [e.created_at for e in trail] == sorted(e.created_at for e in trail)
