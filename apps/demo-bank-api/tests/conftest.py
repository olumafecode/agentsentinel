"""Shared fixtures: a bank with a fixed clock and helpers that call tools like the gateway would."""

import uuid

import pytest
from fastapi.testclient import TestClient

from demo_bank_api.config import Settings
from demo_bank_api.main import create_app
from demo_bank_api.store import BankStore
from sentinel_contracts import TOKEN_HEADER, issue_token, load_key

KEY = load_key("bank-test-key-for-unit-tests-only-0123456789")
ADMIN_KEY = "admin-test-key-0123456789"
NOW = 1_800_000_000.0


class Clock:
    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return Clock(NOW)


@pytest.fixture
def settings():
    return Settings(execution_token_key=KEY, admin_key=ADMIN_KEY)


@pytest.fixture
def store():
    return BankStore()


@pytest.fixture
def client(settings, store, clock):
    with TestClient(create_app(settings, store=store, clock=clock)) as test_client:
        yield test_client


@pytest.fixture
def token_for(clock):
    """Issue a token the way the gateway will for an allowed action."""

    def issue(tool_name, arguments, **overrides):
        params = {
            "key": KEY,
            "correlation_id": str(uuid.uuid4()),
            "tool_name": tool_name,
            "arguments": arguments,
            "customer_scope": "CUS-000123",
            "audience": "demo-bank-api",
            "now": clock(),
        }
        return issue_token(**{**params, **overrides})

    return issue


@pytest.fixture
def call(client, token_for):
    """POST a tool call. Pass token=None to send none, or a string to send that token."""

    def invoke(tool_name, arguments, token="issue"):
        if token == "issue":
            token = token_for(tool_name, arguments)
        headers = {TOKEN_HEADER: token} if token is not None else {}
        return client.post(f"/v1/tools/{tool_name}", json=arguments, headers=headers)

    return invoke
