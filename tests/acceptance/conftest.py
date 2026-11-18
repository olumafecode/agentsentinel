"""The demo bank, the Sentinel Gateway and Vera running together, for the acceptance tests.

Both services are built from environment settings, the way they start in Docker, and
the tests reach them only over HTTP. The bank records every request it receives, so
a test can prove that a blocked action never reached it. Audit records are kept in
memory, or in a fresh PostgreSQL database when a test asks for ``audit_database``.
"""

import os
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import make_conninfo

from banking_agent.agent import Vera
from banking_agent.gateway import GatewayClient
from banking_agent.identity import IdentityStandIn
from demo_bank_api.config import Settings as BankSettings
from demo_bank_api.main import create_app as create_bank
from sentinel_audit.migrate import GATEWAY_ROLE, migrate
from sentinel_contracts import SESSION_HEADER, issue_session_token, load_key
from sentinel_gateway.audit import InMemoryAuditSink
from sentinel_gateway.config import Settings as GatewaySettings
from sentinel_gateway.main import create_app as create_gateway

CUSTOMER_A = "CUS-000123"
CUSTOMER_B = "CUS-000456"


@dataclass
class Stack:
    gateway: TestClient
    bank: TestClient
    audit: InMemoryAuditSink
    session_key: bytes
    agent_key: str
    bank_requests: list = field(default_factory=list)

    def vera(self):
        """Vera talking to this gateway, and the sign-in stand-in that gives her sessions."""
        client = GatewayClient(
            "http://gateway:8000", self.agent_key, client=self.gateway
        )
        return Vera(client, agent_id="AGT-001"), IdentityStandIn(self.session_key)

    def propose(
        self,
        tool_name,
        arguments,
        *,
        customer=CUSTOMER_A,
        task="account_inquiry",
        customer_scope=None,
    ):
        """Send one action from Vera in a session signed in as ``customer``."""
        session_id = f"SES-{secrets.randbelow(10**8):08d}"
        session = issue_session_token(
            key=self.session_key,
            session_id=session_id,
            customer_id=customer,
            agent_id="AGT-001",
            task_type=task,
        )
        body = {
            "correlation_id": str(uuid.uuid4()),
            "session_id": session_id,
            "agent_id": "AGT-001",
            "customer_scope": customer_scope or customer,
            "task_type": task,
            "tool_name": tool_name,
            "arguments": arguments,
            "provenance_labels": {name: "trusted_user_input" for name in arguments},
            "requested_at": datetime.now(UTC).isoformat(),
        }
        return self.gateway.post(
            "/v1/actions/evaluate",
            json=body,
            headers={
                "Authorization": f"Bearer {self.agent_key}",
                SESSION_HEADER: session,
            },
        )


@pytest.fixture
def make_stack():
    """Build a stack. Pass ``audit`` to use another sink, such as the PostgreSQL store."""

    def build(audit=None):
        execution_key = secrets.token_urlsafe(48)
        session_key = secrets.token_urlsafe(48)
        agent_key = secrets.token_urlsafe(48)

        bank = TestClient(
            create_bank(BankSettings.from_env({"EXECUTION_TOKEN_KEY": execution_key}))
        )
        requests = []
        bank.event_hooks = {"request": [requests.append], "response": []}

        audit = InMemoryAuditSink() if audit is None else audit
        gateway_settings = GatewaySettings.from_env(
            {
                "EXECUTION_TOKEN_KEY": execution_key,
                "SESSION_TOKEN_KEY": session_key,
                "AGENT_KEYS": f"AGT-001:{agent_key}",
                "BANK_URL": "http://demo-bank:8001",
            }
        )
        gateway = TestClient(
            create_gateway(gateway_settings, bank_client=bank, audit=audit)
        )
        return Stack(
            gateway=gateway,
            bank=bank,
            audit=audit,
            session_key=load_key(session_key),
            agent_key=agent_key,
            bank_requests=requests,
        )

    return build


@pytest.fixture
def stack(make_stack):
    return make_stack()


@pytest.fixture
def audit_database():
    """A fresh PostgreSQL database with the audit schema, as the gateway's role sees it.

    Needs AUDIT_TEST_DATABASE_URL (an account that can create databases); skips without it.
    """
    admin_url = os.environ.get("AUDIT_TEST_DATABASE_URL")
    if not admin_url:
        pytest.skip("set AUDIT_TEST_DATABASE_URL to run the PostgreSQL tests")
    name = f"acceptance_{uuid.uuid4().hex[:12]}"
    password = "gateway-password-for-acceptance-tests"
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        migrate(make_conninfo(admin_url, dbname=name), password)
        yield make_conninfo(
            admin_url, dbname=name, user=GATEWAY_ROLE, password=password
        )
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )
