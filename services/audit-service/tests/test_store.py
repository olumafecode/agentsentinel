"""The PostgreSQL audit store, its privileges and the tamper test (US-19.1 to US-19.4).

These tests need AUDIT_TEST_DATABASE_URL and are skipped without it.
"""

import threading
import uuid
from itertools import pairwise

import psycopg
import pytest
from psycopg import errors

from sentinel_audit.cli import main
from sentinel_audit.events import GENESIS_HASH
from sentinel_audit.migrate import migrate
from sentinel_audit.store import AuditStore
from sentinel_audit.verify import verify_chain
from sentinel_contracts import AuditEventType


def request_payload(correlation_id, **changes):
    request = {
        "correlation_id": correlation_id,
        "session_id": "SES-00000042",
        "agent_id": "AGT-001",
        "customer_scope": "CUS-000123",
        "task_type": "account_inquiry",
        "tool_name": "get_transactions",
        "arguments": {"customer_id": "CUS-000123", "limit": 5},
        "provenance_labels": {"customer_id": "system"},
        "requested_at": "2027-01-15T08:00:00Z",
    }
    return {"authenticated_agent_id": "AGT-001", "request": {**request, **changes}}


class TestMigrations:
    def test_migrate_creates_the_schema_once(self, database):
        assert migrate(database.admin_url, database.password) == ["001_audit_trail"]
        assert migrate(database.admin_url, database.password) == []

    def test_migrate_refuses_a_short_gateway_password(self, database):
        with pytest.raises(ValueError, match="at least 16"):
            migrate(database.admin_url, "short")

    def test_the_migrate_command_reads_its_settings_from_the_environment(
        self, database, monkeypatch, capsys
    ):
        monkeypatch.setenv("AUDIT_ADMIN_DATABASE_URL", database.admin_url)
        monkeypatch.setenv("AUDIT_GATEWAY_DB_PASSWORD", database.password)

        assert main(["migrate"]) == 0
        assert main(["migrate"]) == 0
        out = capsys.readouterr().out
        assert "Applied 1 migration(s): 001_audit_trail" in out
        assert "already up to date" in out


class TestAppending:
    def test_events_form_a_chain_that_verifies(self, store, trail):
        for event in trail("ALLOW") + trail("BLOCK"):
            store.record(event)

        events = list(store.events())

        assert [e.event_id for e in events] == [f"EVT-00000{n}" for n in range(1, 7)]
        assert events[0].previous_event_hash == GENESIS_HASH
        assert all(b.previous_event_hash == a.event_hash for a, b in pairwise(events))
        assert verify_chain(events).intact

    def test_an_event_reads_back_exactly_as_it_was_hashed(self, store, record):
        written = store.record(
            record(
                payload={
                    "reason_codes": ["UNKNOWN_TOOL"],
                    "note": "café, naïve, 東京",
                    "score": 0.30000000000000004,
                    "nested": {"b": [1, 2.5, None, True], "a": {}},
                },
                policy_version="1.2.0",
                model_version="0.3.1",
            )
        )

        [read] = list(store.events())

        assert read == written
        assert read.computed_hash() == read.event_hash

    def test_a_well_formed_request_is_stored_as_a_tool_call(
        self, migrated, store, record
    ):
        cid = str(uuid.uuid4())
        received = record(
            correlation_id=cid,
            event_type=AuditEventType.ACTION_RECEIVED,
            decision=None,
            payload=request_payload(cid),
        )
        store.record(received)
        store.record(received)
        store.record(
            record(
                event_type=AuditEventType.ACTION_RECEIVED,
                decision=None,
                payload={"request": {"tool_name": "Export-All"}},
            )
        )

        with migrated.admin() as conn:
            rows = conn.execute(
                "SELECT correlation_id, tool_name, arguments FROM audit.tool_calls"
            ).fetchall()
        assert rows == [
            (cid, "get_transactions", {"customer_id": "CUS-000123", "limit": 5})
        ]

    def test_events_for_one_action_can_be_read_alone(self, store, trail):
        first, second = trail(), trail()
        for event in first + second:
            store.record(event)

        events = list(store.events(correlation_id=second[0].correlation_id))

        assert [e.event_type for e in events] == [
            "action_received",
            "decision_made",
            "action_executed",
        ]

    def test_concurrent_writers_keep_one_unbroken_chain(self, store, record):
        def write():
            for _ in range(10):
                store.record(record())

        threads = [threading.Thread(target=write) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        report = verify_chain(store.events())
        assert report.intact
        assert report.checked == 80

    def test_readiness_follows_the_database(self, store):
        assert store.ready()
        broken = AuditStore.connect(
            "postgresql://nobody:wrong@127.0.0.1:1/none", timeout_seconds=0.5
        )
        try:
            assert not broken.ready()
        finally:
            broken.close()


class TestPrivileges:
    @pytest.mark.parametrize(
        "statement",
        [
            "UPDATE audit.events SET actor = 'someone-else'",
            "DELETE FROM audit.events",
            "TRUNCATE audit.events",
            "UPDATE audit.tool_calls SET tool_name = 'export_customers'",
            "DELETE FROM audit.tool_calls",
            "DROP TABLE audit.events",
            "ALTER TABLE audit.events DISABLE TRIGGER events_append_only",
            "SELECT * FROM audit.schema_migrations",
            "CREATE TABLE audit.shadow (id int)",
        ],
    )
    def test_the_gateway_role_can_only_add_and_read(
        self, migrated, store, record, statement
    ):
        store.record(record())

        with migrated.gateway() as conn, pytest.raises(errors.InsufficientPrivilege):
            conn.execute(statement)

    @pytest.mark.parametrize(
        "statement",
        [
            "UPDATE audit.events SET actor = 'someone-else'",
            "DELETE FROM audit.events",
            "TRUNCATE audit.events",
        ],
    )
    def test_even_the_owner_cannot_change_audit_rows(
        self, migrated, store, record, statement
    ):
        store.record(record())

        with (
            migrated.admin() as conn,
            pytest.raises(psycopg.Error, match="append-only"),
        ):
            conn.execute(statement)


class TestTampering:
    def tamper(self, database, statement):
        """Change rows the way a privileged attacker would: switch the guard off first."""
        with database.admin() as conn, conn.transaction():
            conn.execute("ALTER TABLE audit.events DISABLE TRIGGER events_append_only")
            conn.execute(statement)
            conn.execute("ALTER TABLE audit.events ENABLE TRIGGER events_append_only")

    def test_verify_chain_passes_on_an_untouched_chain(
        self, migrated, store, trail, capsys
    ):
        for event in trail():
            store.record(event)

        assert main(["verify-chain", "--database-url", migrated.gateway_url]) == 0
        assert "Checked 3 events: the chain is intact." in capsys.readouterr().out

    def test_verify_chain_reports_an_event_edited_in_the_database(
        self, migrated, store, trail, capsys
    ):
        for event in trail("BLOCK"):
            store.record(event)
        self.tamper(
            migrated,
            "UPDATE audit.events SET decision = 'ALLOW',"
            ' payload = \'{"reason_codes": ["WITHIN_POLICY"]}\''
            " WHERE event_id = 'EVT-000002'",
        )

        code = main(["verify-chain", "--database-url", migrated.gateway_url])

        out = capsys.readouterr().out
        assert code == 1
        assert "the chain is broken" in out
        assert "EVT-000002: event_hash does not match its content" in out

    def test_verify_chain_reports_a_deleted_event(self, migrated, store, trail, capsys):
        for event in trail():
            store.record(event)
        self.tamper(migrated, "DELETE FROM audit.events WHERE event_id = 'EVT-000002'")

        assert main(["verify-chain", "--database-url", migrated.gateway_url]) == 1
        assert "EVT-000003: expected EVT-000002" in capsys.readouterr().out


class TestCompletenessCommand:
    def test_complete_trails_pass(self, migrated, store, trail, capsys):
        for event in trail("ALLOW") + trail("BLOCK"):
            store.record(event)

        assert main(["completeness", "--database-url", migrated.gateway_url]) == 0
        assert (
            "2 actions, 2 with a complete audit trail (100.0%)"
            in capsys.readouterr().out
        )

    def test_a_missing_final_event_fails(self, migrated, store, trail, capsys):
        events = trail("ALLOW")
        for event in events[:2]:
            store.record(event)
        missing = "9b0c4c55-0c9d-4a64-9e5d-4f2d4d8a7a11"

        code = main(
            [
                "completeness",
                "--database-url",
                migrated.gateway_url,
                "--correlation-id",
                missing,
            ]
        )

        out = capsys.readouterr().out
        assert code == 1
        assert "2 actions, 0 with a complete audit trail (0.0%)" in out
        assert f"{events[0].correlation_id}: expected one action_executed" in out
        assert f"{missing}: no audit events at all" in out


def test_commands_explain_a_missing_or_unreachable_database(monkeypatch, capsys):
    monkeypatch.delenv("AUDIT_DATABASE_URL", raising=False)
    monkeypatch.delenv("AUDIT_ADMIN_DATABASE_URL", raising=False)

    assert main(["verify-chain"]) == 2
    assert main(["migrate"]) == 2
    assert (
        main(["verify-chain", "--database-url", "postgresql://x:y@127.0.0.1:1/z"]) == 2
    )
    err = capsys.readouterr().err
    assert "AUDIT_DATABASE_URL is not set" in err
    assert "must both be set" in err
    assert "could not be reached" in err
