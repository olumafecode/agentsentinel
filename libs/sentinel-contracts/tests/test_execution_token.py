"""Tests for signed single-use execution tokens (ADR-010)."""

import base64
import hashlib
import hmac
import json

import pytest

from sentinel_contracts import (
    ReplayGuard,
    TokenError,
    arguments_digest,
    issue_token,
    load_key,
    verify_token,
)
from sentinel_contracts.execution_token import MAX_TTL_SECONDS

KEY = load_key("test-key-for-unit-tests-only-0123456789")
OTHER_KEY = load_key("another-key-that-the-bank-does-not-know-99")
NOW = 1_800_000_000
ARGS = {"customer_id": "CUS-000123", "limit": 20}


def issue(**overrides):
    params = {
        "key": KEY,
        "correlation_id": "3f2b8c1e-5a7d-4e9b-9c1a-2d4f6a8b0c1e",
        "tool_name": "get_transactions",
        "arguments": ARGS,
        "customer_scope": "CUS-000123",
        "audience": "demo-bank-api",
        "now": NOW,
    }
    return issue_token(**{**params, **overrides})


def verify(token, **overrides):
    params = {
        "key": KEY,
        "audience": "demo-bank-api",
        "tool_name": "get_transactions",
        "arguments": ARGS,
        "now": NOW + 1,
    }
    return verify_token(token, **{**params, **overrides})


def reason(token, **overrides):
    with pytest.raises(TokenError) as caught:
        verify(token, **overrides)
    return caught.value.code


def test_valid_token_verifies_and_returns_its_claims():
    claims = verify(issue())
    assert claims.tool_name == "get_transactions"
    assert claims.customer_scope == "CUS-000123"
    assert claims.arguments_sha256 == arguments_digest(ARGS)
    assert claims.expires_at - claims.issued_at == 60


def test_argument_order_does_not_change_the_digest():
    assert arguments_digest({"a": 1, "b": 2}) == arguments_digest({"b": 2, "a": 1})


def test_each_token_has_a_unique_id():
    assert verify(issue()).token_id != verify(issue()).token_id


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"key": OTHER_KEY}, "token_signature_invalid"),
        ({"audience": "approval-service"}, "token_audience_mismatch"),
        ({"tool_name": "export_customers"}, "token_tool_mismatch"),
        (
            {"arguments": {"customer_id": "CUS-000456", "limit": 20}},
            "token_arguments_mismatch",
        ),
        (
            {"arguments": {"customer_id": "CUS-000123", "limit": 100}},
            "token_arguments_mismatch",
        ),
        ({"now": NOW + 60}, "token_expired"),
        ({"now": NOW - 10}, "token_not_yet_valid"),
    ],
)
def test_token_does_not_verify_for_a_different_call(overrides, code):
    assert reason(issue(), **overrides) == code


def test_clock_skew_of_a_few_seconds_is_tolerated():
    assert verify(issue(), now=NOW - 5)


@pytest.mark.parametrize(
    ("token", "code"),
    [
        ("", "token_malformed"),
        ("v1.only-two", "token_malformed"),
        ("v1.a.b.c", "token_malformed"),
        ("v2.e30.e30", "token_version_unsupported"),
        ("v1.e30.!!!*", "token_signature_invalid"),
        ("v1.e30.é", "token_malformed"),
        ("v1.é.abc", "token_malformed"),
    ],
)
def test_malformed_token_is_rejected(token, code):
    assert reason(token) == code


def test_changing_the_claims_breaks_the_signature():
    version, payload, signature = issue().split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["tool_name"] = "export_customers"
    forged = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    assert reason(f"{version}.{forged}.{signature}", tool_name="export_customers") == (
        "token_signature_invalid"
    )


def sign_claims(claims):
    payload = (
        base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    )
    signature = hmac.new(KEY, f"v1.{payload}".encode(), hashlib.sha256).digest()
    return f"v1.{payload}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def valid_claims(**changes):
    claims = {
        "token_id": "abc",
        "correlation_id": "3f2b8c1e-5a7d-4e9b-9c1a-2d4f6a8b0c1e",
        "tool_name": "get_transactions",
        "arguments_sha256": arguments_digest(ARGS),
        "customer_scope": "CUS-000123",
        "issuer": "sentinel-gateway",
        "audience": "demo-bank-api",
        "issued_at": NOW,
        "expires_at": NOW + 60,
    }
    return {**claims, **changes}


@pytest.mark.parametrize(
    ("claims", "code"),
    [
        (valid_claims(issuer="vera"), "token_issuer_invalid"),
        (valid_claims(expires_at=NOW + MAX_TTL_SECONDS + 1), "token_lifetime_invalid"),
        (valid_claims(expires_at=NOW), "token_lifetime_invalid"),
        (valid_claims(issued_at="soon"), "token_malformed"),
        (valid_claims(issued_at=True), "token_malformed"),
        ({"token_id": "abc"}, "token_malformed"),
        ([1, 2, 3], "token_malformed"),
    ],
)
def test_signed_but_invalid_claims_are_rejected(claims, code):
    assert reason(sign_claims(claims)) == code


def test_replay_guard_allows_each_token_once():
    guard = ReplayGuard(clock=lambda: NOW + 1)
    claims = verify(issue())
    guard.consume(claims)
    with pytest.raises(TokenError) as caught:
        guard.consume(claims)
    assert caught.value.code == "token_replayed"


def test_replay_guard_forgets_tokens_after_they_expire():
    moments = iter([NOW + 1, NOW + 61])
    guard = ReplayGuard(clock=lambda: next(moments))
    guard.consume(verify(issue()))
    assert len(guard) == 1
    guard.consume(verify(issue()))
    assert len(guard) == 1


def test_short_keys_are_refused():
    with pytest.raises(TokenError) as caught:
        load_key("too-short")
    assert caught.value.code == "key_too_short"
    with pytest.raises(TokenError):
        issue(key=b"short")


@pytest.mark.parametrize("ttl", [0, MAX_TTL_SECONDS + 1])
def test_lifetime_outside_the_allowed_range_is_refused(ttl):
    with pytest.raises(ValueError, match="ttl_seconds"):
        issue(ttl_seconds=ttl)


def test_arguments_must_be_plain_json():
    with pytest.raises(TypeError):
        issue(arguments={"when": object()})
    with pytest.raises(ValueError, match="JSON compliant"):
        issue(arguments={"amount": float("nan")})
