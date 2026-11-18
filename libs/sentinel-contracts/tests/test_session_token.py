"""Tests for signed customer session tokens (ADR-012)."""

import base64
import hashlib
import hmac
import json

import pytest

from sentinel_contracts import (
    TokenError,
    issue_session_token,
    issue_token,
    load_key,
    verify_session_token,
)
from sentinel_contracts.session_token import (
    DEFAULT_SESSION_TTL_SECONDS,
    MAX_SESSION_TTL_SECONDS,
)

KEY = load_key("session-key-for-unit-tests-only-0123456789")
OTHER_KEY = load_key("another-session-key-nobody-trusts-0123456")
NOW = 1_800_000_000
SESSION = {
    "session_id": "SES-00000042",
    "customer_id": "CUS-000123",
    "agent_id": "AGT-001",
    "task_type": "refund_request",
}


def issue(**overrides):
    return issue_session_token(**{"key": KEY, "now": NOW, **SESSION, **overrides})


def reason(token, *, key=KEY, now=NOW + 1):
    with pytest.raises(TokenError) as caught:
        verify_session_token(token, key=key, now=now)
    return caught.value.code


def sign(claims, key=KEY):
    payload = (
        base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    )
    signature = hmac.new(key, f"s1.{payload}".encode(), hashlib.sha256).digest()
    return f"s1.{payload}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def claims(**changes):
    base = {
        **SESSION,
        "channel": "web_chat",
        "issuer": "veridane-identity",
        "audience": "sentinel-gateway",
        "issued_at": NOW,
        "expires_at": NOW + 1800,
    }
    return {**base, **changes}


def test_a_valid_session_token_verifies_and_returns_its_claims():
    session = verify_session_token(issue(), key=KEY, now=NOW + 60)

    assert session.session_id == "SES-00000042"
    assert session.customer_id == "CUS-000123"
    assert session.agent_id == "AGT-001"
    assert session.task_type == "refund_request"
    assert session.channel == "web_chat"
    assert session.expires_at - session.issued_at == DEFAULT_SESSION_TTL_SECONDS


def test_a_session_token_can_be_used_for_many_actions():
    token = issue()

    for minute in range(0, 30, 5):
        verify_session_token(token, key=KEY, now=NOW + minute * 60)


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"now": NOW + DEFAULT_SESSION_TTL_SECONDS}, "session_expired"),
        ({"now": NOW - 6}, "session_not_yet_valid"),
        ({"key": OTHER_KEY}, "session_signature_invalid"),
    ],
)
def test_a_session_token_fails_when_expired_early_or_foreign(kwargs, code):
    assert reason(issue(), **kwargs) == code


def test_a_few_seconds_of_clock_skew_are_tolerated():
    verify_session_token(issue(), key=KEY, now=NOW - 5)


@pytest.mark.parametrize(
    ("token", "code"),
    [
        ("", "session_malformed"),
        ("s1.only-two", "session_malformed"),
        ("s1.é.abc", "session_malformed"),
        ("v1.e30.e30", "session_version_unsupported"),
    ],
)
def test_a_malformed_session_token_is_rejected(token, code):
    assert reason(token) == code


def test_an_execution_token_is_never_accepted_as_a_session():
    execution = issue_token(
        key=KEY,
        correlation_id="3f2b8c1e-5a7d-4e9b-9c1a-2d4f6a8b0c1e",
        tool_name="get_customer",
        arguments={},
        customer_scope="CUS-000123",
        audience="demo-bank-api",
        now=NOW,
    )

    assert reason(execution) == "session_version_unsupported"


def test_changing_the_customer_breaks_the_signature():
    version, payload, signature = issue().split(".")
    data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    data["customer_id"] = "CUS-000456"
    forged = base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    assert reason(f"{version}.{forged}.{signature}") == "session_signature_invalid"


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (claims(issuer="vera"), "session_issuer_invalid"),
        (claims(audience="demo-bank-api"), "session_audience_mismatch"),
        (claims(expires_at=NOW), "session_lifetime_invalid"),
        (
            claims(expires_at=NOW + MAX_SESSION_TTL_SECONDS + 1),
            "session_lifetime_invalid",
        ),
        (claims(customer_id="Avery"), "session_malformed"),
        (claims(issued_at=True), "session_malformed"),
        (claims(issued_at="1800000000"), "session_malformed"),
        (claims(role="admin"), "session_malformed"),
        ({"session_id": "SES-00000042"}, "session_malformed"),
        ([1, 2, 3], "session_malformed"),
    ],
)
def test_signed_but_invalid_claims_are_rejected(data, code):
    assert reason(sign(data)) == code


@pytest.mark.parametrize(
    "overrides",
    [
        {"ttl_seconds": 0},
        {"ttl_seconds": MAX_SESSION_TTL_SECONDS + 1},
        {"customer_id": "123"},
        {"task_type": "small_talk"},
        {"channel": "Web Chat"},
    ],
)
def test_a_session_token_is_not_issued_with_bad_values(overrides):
    with pytest.raises(ValueError):
        issue(**overrides)


def test_a_short_key_is_refused():
    with pytest.raises(TokenError) as caught:
        issue(key=b"short")
    assert caught.value.code == "key_too_short"
