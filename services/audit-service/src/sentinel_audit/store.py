"""The append-only audit store in PostgreSQL (US-19.2).

The gateway writes through ``AuditStore.record``, which is its audit sink. Each new
event takes the next position in the chain and the hash of the event before it. A
transaction-level lock serialises writers, so the chain stays a single line even
when several gateway threads or replicas write at once.

An ``action_received`` event whose request is well formed also adds a row to
``audit.tool_calls`` in the same transaction.
"""

from collections.abc import Iterator
from datetime import UTC
from typing import Any, Self

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import ValidationError

from sentinel_audit.events import (
    GENESIS_HASH,
    StoredEvent,
    event_hash,
    event_id_for,
    timestamp_text,
)
from sentinel_contracts import AuditEventType, AuditRecord, ProtectedActionRequest

_CHAIN_LOCK = 7_021_786_416_712_066_002
_COLUMNS = (
    "position, event_id, correlation_id, event_type, actor, decision, policy_version,"
    " model_version, payload, created_at, previous_event_hash, event_hash"
)


class AuditStore:
    """Reads and appends audit events. Safe to share between threads."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    @classmethod
    def connect(
        cls,
        url: str,
        *,
        max_connections: int = 10,
        timeout_seconds: float = 5.0,
        wait: bool = False,
    ) -> Self:
        """Open a connection pool.

        By default connections are made in the background, so a gateway can start
        while the database is still starting; it reports not ready until then. With
        ``wait`` the call fails at once if the database cannot be reached.
        """
        pool = ConnectionPool(
            url,
            min_size=1,
            max_size=max_connections,
            timeout=timeout_seconds,
            open=False,
            name="sentinel-audit",
        )
        pool.open(wait=wait, timeout=timeout_seconds)
        return cls(pool)

    def record(self, event: AuditRecord) -> StoredEvent:
        """Append one event to the chain and return it as stored."""
        with self._pool.connection() as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (_CHAIN_LOCK,))
            last = conn.execute(
                "SELECT position, event_hash FROM audit.events"
                " ORDER BY position DESC LIMIT 1"
            ).fetchone()
            position = last[0] + 1 if last else 1
            stored = _chained(event, position, last[1] if last else GENESIS_HASH)
            if event.event_type is AuditEventType.ACTION_RECEIVED:
                _record_tool_call(conn, event.payload.get("request"))
            conn.execute(
                f"INSERT INTO audit.events ({_COLUMNS})"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    stored.position,
                    stored.event_id,
                    stored.correlation_id,
                    stored.event_type,
                    stored.actor,
                    stored.decision,
                    stored.policy_version,
                    stored.model_version,
                    Jsonb(stored.payload),
                    stored.created_at,
                    stored.previous_event_hash,
                    stored.event_hash,
                ),
            )
        return stored

    def events(self, *, correlation_id: str | None = None) -> Iterator[StoredEvent]:
        """Every event in chain order, or only those for one action."""
        query = f"SELECT {_COLUMNS} FROM audit.events"
        params: tuple[Any, ...] = ()
        if correlation_id is not None:
            query += " WHERE correlation_id = %s"
            params = (correlation_id,)
        query += " ORDER BY position"
        with (
            self._pool.connection() as conn,
            conn.transaction(),
            conn.cursor(name="audit_events", row_factory=dict_row) as cursor,
        ):
            cursor.itersize = 500
            cursor.execute(query, params)
            for row in cursor:
                yield StoredEvent(**row)

    def ready(self) -> bool:
        """True when the database answers and the audit tables can be read."""
        try:
            with self._pool.connection(timeout=2.0) as conn:
                conn.execute("SELECT 1 FROM audit.events LIMIT 0")
        except psycopg.Error:
            return False
        return True

    def close(self) -> None:
        self._pool.close()


def _chained(event: AuditRecord, position: int, previous_hash: str) -> StoredEvent:
    created_at = event.created_at.astimezone(UTC)
    fields = {
        "event_id": event_id_for(position),
        "correlation_id": event.correlation_id,
        "event_type": event.event_type.value,
        "actor": event.actor,
        "decision": event.decision.value if event.decision else None,
        "policy_version": event.policy_version,
        "model_version": event.model_version,
        "payload": event.model_dump(mode="json")["payload"],
        "created_at": timestamp_text(created_at),
        "previous_event_hash": previous_hash,
    }
    return StoredEvent(
        position=position,
        **{**fields, "created_at": created_at},
        event_hash=event_hash(fields),
    )


def _record_tool_call(conn: Any, request: Any) -> None:
    try:
        call = ProtectedActionRequest.model_validate(request)
    except ValidationError:
        return
    data = call.model_dump(mode="json")
    conn.execute(
        "INSERT INTO audit.tool_calls (correlation_id, session_id, agent_id,"
        " customer_scope, task_type, tool_name, arguments, provenance_labels,"
        " requested_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        " ON CONFLICT (correlation_id) DO NOTHING",
        (
            call.correlation_id,
            call.session_id,
            call.agent_id,
            call.customer_scope,
            call.task_type.value,
            call.tool_name,
            Jsonb(data["arguments"]),
            Jsonb(data["provenance_labels"]),
            call.requested_at,
        ),
    )
