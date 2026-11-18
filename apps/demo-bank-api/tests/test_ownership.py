"""The gateway-only lookup of who owns each account, transaction and dispute (US-01.1)."""

import pytest

from sentinel_contracts import TOKEN_HEADER
from sentinel_contracts.ownership import (
    MAX_OWNERSHIP_QUERY,
    OWNERSHIP_PATH,
    OWNERSHIP_TOOL,
)


@pytest.fixture
def lookup(client, token_for):
    """POST an ownership lookup. Pass token=None to send none, or a string to send that token."""

    def ask(body, token="issue"):
        if token == "issue":
            token = token_for(OWNERSHIP_TOOL, body)
        headers = {TOKEN_HEADER: token} if token is not None else {}
        return client.post(OWNERSHIP_PATH, json=body, headers=headers)

    return ask


def test_the_bank_names_the_owner_of_each_record(lookup):
    body = {
        "identifiers": [
            "ACC-00000123",
            "TXN-0000004568",
            "DSP-000001",
            "ACC-99000017",
            "TXN-0000004570",
        ]
    }

    response = lookup(body)

    assert response.status_code == 200
    assert response.json() == {
        "owners": {
            "ACC-00000123": "CUS-000123",
            "TXN-0000004568": "CUS-000123",
            "DSP-000001": "CUS-000123",
            "ACC-99000017": "CUS-990001",
            "TXN-0000004570": "CUS-000456",
        }
    }


def test_a_record_the_bank_does_not_have_has_no_owner(lookup):
    response = lookup({"identifiers": ["ACC-12345678", "DSP-999999"]})

    assert response.json() == {"owners": {"ACC-12345678": None, "DSP-999999": None}}


def test_a_refund_made_today_is_owned_like_its_account(client, call, lookup):
    refund = call(
        "issue_refund",
        {
            "account_id": "ACC-00000123",
            "amount": "20.00",
            "original_transaction_id": "TXN-0000004568",
            "reason": "Partial refund",
        },
    ).json()["result"]

    owners = lookup({"identifiers": [refund["transaction_id"]]}).json()["owners"]

    assert owners == {refund["transaction_id"]: "CUS-000123"}


@pytest.mark.parametrize(
    "body",
    [
        {"identifiers": []},
        {"identifiers": ["CUS-000123"]},
        {"identifiers": ["ACC-00000123", "ACC-00000123"]},
        {"identifiers": [f"ACC-{n:08d}" for n in range(MAX_OWNERSHIP_QUERY + 1)]},
        {"identifiers": "ACC-00000123"},
        {"accounts": ["ACC-00000123"]},
    ],
)
def test_a_malformed_lookup_is_refused(lookup, body):
    response = lookup(body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_arguments"


def test_the_lookup_needs_a_token(lookup):
    response = lookup({"identifiers": ["ACC-00000123"]}, token=None)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "missing_token"


def test_a_tool_token_does_not_open_the_lookup(lookup, token_for):
    body = {"identifiers": ["ACC-00000123"]}

    response = lookup(body, token=token_for("get_customer", body))

    assert response.json()["error"]["code"] == "token_tool_mismatch"


def test_a_lookup_token_does_not_open_a_tool(call, token_for):
    arguments = {"customer_id": "CUS-000123"}

    response = call(
        "get_customer", arguments, token=token_for(OWNERSHIP_TOOL, arguments)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "token_tool_mismatch"


def test_a_lookup_token_works_once_and_only_for_its_records(lookup, token_for):
    body = {"identifiers": ["ACC-00000123"]}
    token = token_for(OWNERSHIP_TOOL, body)

    assert lookup(body, token=token).status_code == 200
    assert lookup(body, token=token).json()["error"]["code"] == "token_replayed"
    other = {"identifiers": ["ACC-00000456"]}
    assert (
        lookup(other, token=token_for(OWNERSHIP_TOOL, body)).json()["error"]["code"]
        == "token_arguments_mismatch"
    )


def test_the_lookup_is_not_offered_to_agents(client):
    names = [tool["tool_name"] for tool in client.get("/v1/tools").json()["tools"]]

    assert OWNERSHIP_TOOL not in names
