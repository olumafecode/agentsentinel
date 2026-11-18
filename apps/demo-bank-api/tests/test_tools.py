"""Each bank tool does what its description says (US-16.1, US-16.3)."""

from decimal import Decimal

import pytest

from demo_bank_api.tools import TOOLS


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()["result"]


def error_code(response):
    return response.json()["error"]["code"]


def test_catalogue_lists_every_tool_with_its_argument_schema(client):
    response = client.get("/v1/tools")
    assert response.status_code == 200
    entries = {entry["tool_name"]: entry for entry in response.json()["tools"]}
    assert set(entries) == set(TOOLS)
    refund = entries["issue_refund"]
    assert refund["category"] == "financial"
    assert refund["high_impact"] is True
    assert refund["sensitive_parameters"] == ["account_id", "amount"]
    assert set(refund["arguments_schema"]["required"]) == {
        "account_id",
        "amount",
        "original_transaction_id",
        "reason",
    }


def test_get_customer_returns_the_profile_and_address(call):
    customer = ok(call("get_customer", {"customer_id": "CUS-000123"}))
    assert customer["full_name"] == "Avery Stone"
    assert customer["email"] == "avery.stone123@example.com"
    assert customer["address"] == "12 Example Street, Sampletown, ZZ 00000"


def test_get_accounts_returns_only_that_customers_accounts(call):
    accounts = ok(call("get_accounts", {"customer_id": "CUS-990001"}))
    assert [a["account_id"] for a in accounts] == ["ACC-99000017", "ACC-99000042"]
    assert {a["customer_id"] for a in accounts} == {"CUS-990001"}


def test_get_transactions_returns_only_that_customers_transactions(call, store):
    """US-16 acceptance criterion 1."""
    transactions = ok(
        call("get_transactions", {"customer_id": "CUS-000123", "limit": 100})
    )
    own_accounts = {a.account_id for a in store.list_accounts("CUS-000123")}
    assert transactions
    assert {t["account_id"] for t in transactions} <= own_accounts
    assert "TXN-0000004570" not in {t["transaction_id"] for t in transactions}


def test_get_transactions_is_newest_first_and_respects_the_limit(call):
    transactions = ok(
        call("get_transactions", {"customer_id": "CUS-000001", "limit": 5})
    )
    assert len(transactions) == 5
    times = [t["created_at"] for t in transactions]
    assert times == sorted(times, reverse=True)


def test_get_transactions_returns_twenty_by_default(call, store):
    available = len(store.list_transactions("CUS-000001", 100))
    assert len(ok(call("get_transactions", {"customer_id": "CUS-000001"}))) == min(
        20, available
    )


def test_update_address_changes_the_address(call):
    result = ok(
        call(
            "update_address",
            {"customer_id": "CUS-000123", "address": " 7 Example Road "},
        )
    )
    assert result == {"customer_id": "CUS-000123", "address": "7 Example Road"}
    assert (
        ok(call("get_customer", {"customer_id": "CUS-000123"}))["address"]
        == "7 Example Road"
    )


def test_issue_refund_credits_the_account_and_records_a_refund(call, store):
    before = store.list_accounts("CUS-000123")[0].balance
    refund = ok(
        call(
            "issue_refund",
            {
                "account_id": "ACC-00000123",
                "amount": "120.00",
                "original_transaction_id": "TXN-0000004568",
                "reason": "Item returned",
            },
        )
    )
    assert refund["transaction_type"] == "refund"
    assert refund["amount"] == "120.00"
    assert refund["related_transaction_id"] == "TXN-0000004568"
    assert refund["transaction_id"] == "TXN-0000004571"
    assert store.list_accounts("CUS-000123")[0].balance == before + Decimal("120.00")


def test_refunds_cannot_exceed_the_original_purchase(call):
    first = {
        "account_id": "ACC-00000123",
        "amount": "100.00",
        "original_transaction_id": "TXN-0000004568",
        "reason": "Partial refund",
    }
    ok(call("issue_refund", first))
    second = call("issue_refund", {**first, "amount": "20.01"})
    assert second.status_code == 409
    assert error_code(second) == "refund_exceeds_original"
    ok(call("issue_refund", {**first, "amount": "20.00"}))


@pytest.mark.parametrize(
    ("changes", "status", "code"),
    [
        ({"original_transaction_id": "TXN-0000009999"}, 404, "transaction_not_found"),
        ({"account_id": "ACC-00009999"}, 404, "account_not_found"),
        ({"amount": "751.00"}, 409, "refund_exceeds_original"),
    ],
)
def test_refund_problems_are_reported(call, changes, status, code):
    arguments = {
        "account_id": "ACC-00000123",
        "amount": "750.00",
        "original_transaction_id": "TXN-0000004567",
        "reason": "Duplicate charge",
        **changes,
    }
    response = call("issue_refund", arguments)
    assert response.status_code == status
    assert error_code(response) == code


def test_only_purchases_can_be_refunded(call, store):
    deposit = next(
        t.transaction_id
        for t in store.list_transactions("CUS-000001", 100)
        if t.transaction_type.value != "purchase"
    )
    response = call(
        "issue_refund",
        {
            "account_id": "ACC-00000001",
            "amount": "1.00",
            "original_transaction_id": deposit,
            "reason": "Not a purchase",
        },
    )
    assert response.status_code == 409
    assert error_code(response) == "not_refundable"


def test_refund_to_a_frozen_account_is_refused(call):
    ok(
        call(
            "freeze_account",
            {"account_id": "ACC-00000123", "reason": "Suspected fraud"},
        )
    )
    response = call(
        "issue_refund",
        {
            "account_id": "ACC-00000123",
            "amount": "10.00",
            "original_transaction_id": "TXN-0000004568",
            "reason": "Item returned",
        },
    )
    assert response.status_code == 409
    assert error_code(response) == "account_not_open"


def test_refund_to_another_customers_account_is_possible_at_the_bank(call):
    """The bank does not judge intent: stopping this is the gateway's job (UC-02)."""
    refund = ok(
        call(
            "issue_refund",
            {
                "account_id": "ACC-99000017",
                "amount": "150.00",
                "original_transaction_id": "TXN-0000004567",
                "reason": "Refund to new account",
            },
        )
    )
    assert refund["account_id"] == "ACC-99000017"


def test_close_dispute_closes_it_once(call):
    arguments = {"dispute_id": "DSP-000001", "resolution": "Duplicate charge reversed"}
    dispute = ok(call("close_dispute", arguments))
    assert dispute["status"] == "closed"
    assert dispute["resolution"] == "Duplicate charge reversed"
    assert dispute["closed_at"].startswith("2027-01-15")
    again = call("close_dispute", arguments)
    assert again.status_code == 409
    assert error_code(again) == "dispute_already_closed"


def test_export_customers_returns_every_customer(call, store):
    customers = ok(call("export_customers", {}))
    assert len(customers) == store.counts()["customers"]


def test_reset_credentials_returns_a_reference(call):
    first = ok(call("reset_credentials", {"customer_id": "CUS-000456"}))
    second = ok(call("reset_credentials", {"customer_id": "CUS-000456"}))
    assert first["reset_reference"] == "RST-000001"
    assert second["reset_reference"] == "RST-000002"


def test_freeze_account_sets_the_status(call):
    account = ok(
        call("freeze_account", {"account_id": "ACC-00000456", "reason": "Lost card"})
    )
    assert account["status"] == "frozen"


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("get_customer", {"customer_id": "CUS-999999"}),
        ("get_accounts", {"customer_id": "CUS-999999"}),
        ("get_transactions", {"customer_id": "CUS-999999"}),
        (
            "update_address",
            {"customer_id": "CUS-999999", "address": "1 Example Street"},
        ),
        ("reset_credentials", {"customer_id": "CUS-999999"}),
        ("freeze_account", {"account_id": "ACC-99999999", "reason": "Test"}),
        ("close_dispute", {"dispute_id": "DSP-999999", "resolution": "Test"}),
    ],
)
def test_unknown_records_return_404(call, tool_name, arguments):
    assert call(tool_name, arguments).status_code == 404


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("get_customer", {}),
        ("get_customer", {"customer_id": "123"}),
        ("get_customer", {"customer_id": "CUS-000123", "include": "everything"}),
        ("get_transactions", {"customer_id": "CUS-000123", "limit": 0}),
        ("get_transactions", {"customer_id": "CUS-000123", "limit": 101}),
        ("update_address", {"customer_id": "CUS-000123", "address": "x"}),
        ("export_customers", {"format": "csv"}),
        (
            "issue_refund",
            {
                "account_id": "ACC-00000123",
                "amount": "-5.00",
                "original_transaction_id": "TXN-0000004568",
                "reason": "Negative",
            },
        ),
        (
            "issue_refund",
            {
                "account_id": "ACC-00000123",
                "amount": "1.005",
                "original_transaction_id": "TXN-0000004568",
                "reason": "Too precise",
            },
        ),
    ],
)
def test_invalid_arguments_return_422(call, tool_name, arguments):
    response = call(tool_name, arguments)
    assert response.status_code == 422
    assert error_code(response) == "invalid_arguments"
    assert response.json()["error"]["details"]


def test_unknown_tool_returns_404(call):
    response = call("transfer_everything", {})
    assert response.status_code == 404
    assert error_code(response) == "unknown_tool"
