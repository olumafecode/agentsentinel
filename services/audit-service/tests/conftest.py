"""Fixtures for the audit tests.

The PostgreSQL tests need a server and an account that can create databases, given as
AUDIT_TEST_DATABASE_URL (CI starts one). Each test gets a fresh database, because an
append-only table cannot be emptied between tests. Without the variable those tests
are skipped and the rest still run.
"""

import os
import uuid
from datetime import UTC, datetime

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from sentinel_audit.migrate import GATEWAY_ROLE, migrate
from sentinel_audit.store import AuditStore
from sentinel_contracts import AuditEventType, AuditRecord, Decision

ADMIN_URL = os.environ.get("AUDIT_TEST_DATABASE_URL")
GATEWAY_PASSWORD = "gateway-password-for-tests-only"


class Database:
    password = GATEWAY_PASSWORD

    def __init__(self, name: str) -> None:
        self.admin_url = make_conninfo(ADMIN_URL, dbname=name)
        self.gateway_url = make_conninfo(
            ADMIN_URL, dbname=name, user=GATEWAY_ROLE, password=GATEWAY_PASSWORD
        )

    def admin(self) -> psycopg.Connection:
        return psycopg.connect(self.admin_url, autocommit=True)

    def gateway(self) -> psycopg.Connection:
        return psycopg.connect(self.gateway_url, autocommit=True)


@pytest.fixture
def database():
    """A new, empty database, dropped after the test. Skips without a server."""
    if not ADMIN_URL:
        pytest.skip("set AUDIT_TEST_DATABASE_URL to run the PostgreSQL tests")
    name = f"audit_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    yield Database(name)
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(
            sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
        )


@pytest.fixture
def migrated(database):
    migrate(database.admin_url, GATEWAY_PASSWORD)
    return database


@pytest.fixture
def store(migrated):
    """The store as the gateway uses it, connected with the gateway's own role."""
    audit = AuditStore.connect(migrated.gateway_url, wait=True)
    yield audit
    audit.close()


@pytest.fixture
def record():
    """Build an AuditRecord; keyword arguments replace the defaults."""

    def build(**changes):
        fields = {
            "correlation_id": str(uuid.uuid4()),
            "event_type": AuditEventType.DECISION_MADE,
            "actor": "sentinel-gateway",
            "decision": Decision.BLOCK,
            "payload": {"reason_codes": ["UNKNOWN_TOOL"], "summary": "Blocked."},
            "created_at": datetime(2027, 1, 15, 8, 0, 0, 123456, tzinfo=UTC),
        }
        return AuditRecord(**{**fields, **changes})

    return build


@pytest.fixture
def trail(record):
    """The three records the gateway writes for one action."""

    def build(decision="ALLOW", correlation_id=None):
        cid = correlation_id or str(uuid.uuid4())
        final = {
            "ALLOW": AuditEventType.ACTION_EXECUTED,
            "HUMAN_REVIEW": AuditEventType.APPROVAL_REQUESTED,
            "BLOCK": AuditEventType.ACTION_STOPPED,
            "QUARANTINE": AuditEventType.ACTION_STOPPED,
        }[decision]
        return [
            record(
                correlation_id=cid,
                event_type=AuditEventType.ACTION_RECEIVED,
                decision=None,
                payload={"request": {"tool_name": "get_customer"}},
            ),
            record(
                correlation_id=cid,
                decision=decision,
                payload={"reason_codes": ["WITHIN_POLICY"], "summary": "Fine."},
            ),
            record(correlation_id=cid, event_type=final, decision=decision, payload={}),
        ]

    return build
