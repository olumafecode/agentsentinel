"""Forwarding allowed calls to the bank, and every way the bank can answer (US-18.4)."""

import json

import httpx2
import pytest

from sentinel_contracts import TOKEN_HEADER, ExecutionStatus
from sentinel_gateway.bank import BankClient

ARGUMENTS = {"limit": 2, "customer_id": "CUS-000123"}


def client_for(handler):
    return BankClient(
        "http://bank.test/",
        client=httpx2.Client(transport=httpx2.MockTransport(handler)),
        clock=lambda: 1_800_000_000.0,
    )


def test_the_call_carries_the_token_and_the_canonical_arguments():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["token"] = request.headers[TOKEN_HEADER]
        seen["body"] = request.content
        return httpx2.Response(
            200, json={"tool_name": "get_transactions", "result": []}
        )

    result = client_for(handler).execute("get_transactions", ARGUMENTS, "v1.token.sig")

    assert seen == {
        "url": "http://bank.test/v1/tools/get_transactions",
        "token": "v1.token.sig",
        "body": b'{"customer_id":"CUS-000123","limit":2}',
    }
    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.result == []
    assert result.http_status == 200
    assert result.error is None
    assert result.completed_at.timestamp() == 1_800_000_000.0


@pytest.mark.parametrize(
    ("status", "body", "expected", "code"),
    [
        (
            409,
            {"error": {"code": "account_not_open", "message": "closed"}},
            "rejected",
            "account_not_open",
        ),
        (
            403,
            {"error": {"code": "token_replayed", "message": "used"}},
            "rejected",
            "token_replayed",
        ),
        (422, {"detail": "unexpected shape"}, "rejected", "bank_error"),
        (500, None, "failed", "bank_error"),
        (502, {"error": {"code": "", "message": "x"}}, "failed", "bank_error"),
        (200, {"tool_name": "get_customer"}, "failed", "bank_error"),
    ],
)
def test_a_bank_error_becomes_an_execution_result(status, body, expected, code):
    def handler(request):
        content = b"not json" if body is None else json.dumps(body).encode()
        return httpx2.Response(status, content=content)

    result = client_for(handler).execute("get_customer", {}, "token")

    assert result.status == expected
    assert result.http_status == status
    assert result.error.code == code
    assert result.result is None


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (httpx2.ConnectError("refused"), "bank_unreachable"),
        (httpx2.ReadTimeout("slow"), "bank_timeout"),
    ],
)
def test_an_unreachable_bank_is_a_failed_execution(error, code):
    def handler(request):
        raise error

    result = client_for(handler).execute("get_customer", {}, "token")

    assert result.status is ExecutionStatus.FAILED
    assert result.http_status is None
    assert result.error.code == code


def test_long_bank_messages_are_cut_to_fit_the_contract():
    def handler(request):
        return httpx2.Response(
            409, json={"error": {"code": "c" * 100, "message": "m" * 1000}}
        )

    error = client_for(handler).execute("get_customer", {}, "token").error

    assert (len(error.code), len(error.message)) == (64, 300)


def test_a_client_passed_in_is_left_open():
    passed_in = httpx2.Client()

    BankClient("http://bank.test", client=passed_in).close()

    assert not passed_in.is_closed
