"""Only gateway-signed, single-use, exactly matching calls reach a tool (US-16, ADR-010)."""

import pytest

from demo_bank_api.tools import TOOLS
from sentinel_contracts import load_key

ARGS = {"customer_id": "CUS-000123", "limit": 5}


def code(response):
    return response.json()["error"]["code"]


@pytest.mark.parametrize("tool_name", sorted(TOOLS))
def test_every_tool_refuses_a_call_without_a_token(call, tool_name, store):
    before = store.checksum()
    response = call(tool_name, {"customer_id": "CUS-000123"}, token=None)
    assert response.status_code == 403
    assert code(response) == "missing_token"
    assert store.checksum() == before


def test_a_made_up_token_is_refused(call):
    response = call("get_transactions", ARGS, token="v1.e30.c2lnbmF0dXJl")
    assert response.status_code == 403
    assert code(response) == "token_signature_invalid"


def test_a_token_signed_with_another_key_is_refused(call, token_for):
    other_key = load_key("a-key-the-bank-has-never-seen-0123456789")
    response = call(
        "get_transactions",
        ARGS,
        token=token_for("get_transactions", ARGS, key=other_key),
    )
    assert code(response) == "token_signature_invalid"


def test_a_token_for_another_tool_is_refused(call, token_for):
    response = call("export_customers", {}, token=token_for("get_transactions", {}))
    assert response.status_code == 403
    assert code(response) == "token_tool_mismatch"


def test_changed_arguments_are_refused(call, token_for):
    """A token allowed for Customer A cannot be used to read Customer B."""
    token = token_for("get_transactions", ARGS)
    response = call(
        "get_transactions", {**ARGS, "customer_id": "CUS-000456"}, token=token
    )
    assert response.status_code == 403
    assert code(response) == "token_arguments_mismatch"


def test_a_refund_amount_cannot_be_raised_after_approval(call, token_for, store):
    allowed = {
        "account_id": "ACC-00000123",
        "amount": "10.00",
        "original_transaction_id": "TXN-0000004567",
        "reason": "Partial refund",
    }
    before = store.checksum()
    response = call(
        "issue_refund",
        {**allowed, "amount": "750.00"},
        token=token_for("issue_refund", allowed),
    )
    assert code(response) == "token_arguments_mismatch"
    assert store.checksum() == before


def test_a_token_works_only_once(call, token_for):
    token = token_for("get_transactions", ARGS)
    assert call("get_transactions", ARGS, token=token).status_code == 200
    replay = call("get_transactions", ARGS, token=token)
    assert replay.status_code == 403
    assert code(replay) == "token_replayed"


def test_an_expired_token_is_refused(call, token_for, clock):
    token = token_for("get_transactions", ARGS)
    clock.now += 61
    response = call("get_transactions", ARGS, token=token)
    assert code(response) == "token_expired"


def test_a_token_for_another_service_is_refused(call, token_for):
    token = token_for("get_transactions", ARGS, audience="approval-service")
    assert (
        code(call("get_transactions", ARGS, token=token)) == "token_audience_mismatch"
    )


def test_the_response_names_the_correlation_id_from_the_token(call, token_for):
    token = token_for(
        "get_transactions", ARGS, correlation_id="3f2b8c1e-5a7d-4e9b-9c1a-2d4f6a8b0c1e"
    )
    response = call("get_transactions", ARGS, token=token)
    assert response.json()["correlation_id"] == "3f2b8c1e-5a7d-4e9b-9c1a-2d4f6a8b0c1e"


@pytest.mark.parametrize(
    ("body", "status", "error"),
    [
        (b"not json", 400, "invalid_json"),
        (b"[1, 2]", 400, "invalid_json"),
        (b"\xff\xfe", 400, "invalid_json"),
        (b'{"a": "' + b"x" * 70_000 + b'"}', 413, "body_too_large"),
    ],
)
def test_malformed_bodies_are_refused(client, body, status, error):
    response = client.post(
        "/v1/tools/get_customer", content=body, headers={"X-Execution-Token": "v1.a.b"}
    )
    assert response.status_code == status
    assert response.json()["error"]["code"] == error


def test_catalogue_and_health_need_no_token(client):
    for path in ("/v1/tools", "/healthz", "/readyz"):
        assert client.get(path).status_code == 200
