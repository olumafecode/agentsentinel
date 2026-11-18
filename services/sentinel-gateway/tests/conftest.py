"""Shared fixtures: a gateway wired to an in-process demo bank, both on one fixed clock."""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from demo_bank_api.config import Settings as BankSettings
from demo_bank_api.main import create_app as create_bank
from demo_bank_api.store import BankStore
from sentinel_contracts import SESSION_HEADER, issue_session_token, load_key
from sentinel_gateway.audit import InMemoryAuditSink
from sentinel_gateway.auth import AgentKeyring
from sentinel_gateway.config import Settings
from sentinel_gateway.main import create_app
from sentinel_gateway.registry import AgentProfile, AgentRegistry, AgentStatus

EXECUTION_KEY = load_key("execution-key-for-gateway-tests-0123456789")
SESSION_KEY = load_key("session-key-for-gateway-tests-0123456789ab")
AGENT_KEYS = {
    "AGT-001": "vera-api-key-for-gateway-tests-0123456789",
    "AGT-002": "atlas-api-key-for-gateway-tests-012345678",
}
NOW = 1_800_000_000.0

SESSION = {
    "session_id": "SES-00000042",
    "customer_id": "CUS-000123",
    "agent_id": "AGT-001",
    "task_type": "account_inquiry",
}


class Clock:
    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def atlas() -> AgentProfile:
    """A second registered agent, for tests about agents acting for each other."""
    return AgentProfile(
        agent_id="AGT-002",
        name="Atlas",
        role="customer_service",
        allowed_tools=("get_customer",),
        status=AgentStatus.ACTIVE,
        review_threshold=0.6,
        block_threshold=0.85,
        created_at=datetime(2026, 1, 5, tzinfo=UTC),
    )


@pytest.fixture
def clock():
    return Clock(NOW)


@pytest.fixture
def agent_keys():
    """Each test agent's API key, by agent ID."""
    return dict(AGENT_KEYS)


@pytest.fixture
def settings():
    return Settings(
        execution_token_key=EXECUTION_KEY,
        session_token_key=SESSION_KEY,
        agent_keys=AgentKeyring(AGENT_KEYS),
        bank_url="http://bank.test",
    )


@pytest.fixture
def agents():
    registry = AgentRegistry.load()
    return AgentRegistry([registry.get("AGT-001"), atlas()])


@pytest.fixture
def bank_store():
    return BankStore()


@pytest.fixture
def bank(bank_store, clock):
    """The demo bank, reached in process. ``bank.calls`` counts every request it gets."""
    app = create_bank(
        BankSettings(execution_token_key=EXECUTION_KEY), store=bank_store, clock=clock
    )
    client = TestClient(app)
    client.calls = []
    client.event_hooks = {"request": [client.calls.append], "response": []}
    return client


@pytest.fixture
def refunds_for(bank_store):
    """List the refunds the bank has made against one of CUS-000123's purchases."""

    def find(transaction_id):
        return [
            txn
            for txn in bank_store.list_transactions("CUS-000123", 100)
            if txn.related_transaction_id == transaction_id
        ]

    return find


@pytest.fixture
def audit():
    return InMemoryAuditSink()


@pytest.fixture
def make_gateway(settings, agents, bank, audit, clock):
    """Build a gateway client; keyword arguments go to create_app."""

    def build(**overrides):
        params = {
            "agents": agents,
            "bank_client": bank,
            "audit": audit,
            "clock": clock,
        }
        return TestClient(create_app(settings, **{**params, **overrides}))

    return build


@pytest.fixture
def gateway(make_gateway):
    return make_gateway()


class UnreachableBank:
    """A bank connection that always fails, so an allowed call's token stays unused."""

    def post(self, *args, **kwargs):
        raise ConnectionError("bank unreachable")

    def close(self):
        pass


@pytest.fixture
def offline_gateway(make_gateway):
    """A gateway that decides normally but cannot reach the bank."""
    return make_gateway(bank_client=UnreachableBank())


@pytest.fixture
def session_token(clock):
    """Sign a session token the way Veridane identity would."""

    def issue(**overrides):
        return issue_session_token(
            key=SESSION_KEY, now=clock(), **{**SESSION, **overrides}
        )

    return issue


@pytest.fixture
def action(clock):
    """Build a valid request body for a lookup in the standard session."""

    def build(**overrides):
        body = {
            "correlation_id": str(uuid.uuid4()),
            "session_id": SESSION["session_id"],
            "agent_id": SESSION["agent_id"],
            "customer_scope": SESSION["customer_id"],
            "task_type": SESSION["task_type"],
            "tool_name": "get_transactions",
            "arguments": {"customer_id": "CUS-000123", "limit": 2},
            "provenance_labels": {"customer_id": "system"},
            "requested_at": datetime.fromtimestamp(clock(), tz=UTC).isoformat(),
        }
        return {**body, **overrides}

    return build


@pytest.fixture
def evaluate(gateway, session_token):
    """POST an action as an agent.

    ``agent`` picks whose key is sent (None sends no key); ``key`` sends that exact
    key instead. ``session`` is a token to send, "issue" for the standard session, or
    None for no session token.
    """

    def send(body, *, agent="AGT-001", key=None, session="issue", client=None):
        headers = {}
        key = key or (AGENT_KEYS[agent] if agent else None)
        if key is not None:
            headers["Authorization"] = f"Bearer {key}"
        if session == "issue":
            session = session_token()
        if session is not None:
            headers[SESSION_HEADER] = session
        return (client or gateway).post(
            "/v1/actions/evaluate", json=body, headers=headers
        )

    return send


@pytest.fixture
def refund(action):
    """Build a refund of 120.00 for TXN-0000004568 in a refund_request session."""

    def build(**overrides):
        body = action(
            task_type="refund_request",
            tool_name="issue_refund",
            arguments={
                "account_id": "ACC-00000123",
                "amount": "120.00",
                "original_transaction_id": "TXN-0000004568",
                "reason": "Duplicate charge",
            },
            provenance_labels={
                "account_id": "trusted_user_input",
                "amount": "trusted_user_input",
                "original_transaction_id": "system",
                "reason": "trusted_user_input",
            },
        )
        return {**body, **overrides}

    return build


@pytest.fixture
def refund_session(session_token):
    """A session token for a refund_request session."""
    return session_token(task_type="refund_request")
