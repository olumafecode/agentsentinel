"""Where the gateway sends its audit records (FR-13, NFR-06).

Every evaluated action produces action_received, decision_made and then one of
action_executed, approval_requested or action_stopped.

- With AUDIT_DATABASE_URL set, the records go to the hash-linked audit trail in
  PostgreSQL (``sentinel_audit.store.AuditStore``, US-19), written with the gateway's
  own database role, which can add rows but never change or delete them.
- Without it, JsonLinesAuditSink writes each record as one line of JSON to standard
  output. That is for local runs only; nothing is chained.

If either of the first two records cannot be written, the gateway refuses the action
rather than run it unaudited.

A sink may also offer ``ready()`` for the readiness probe and ``close()`` for shutdown.
"""

import sys
import threading
from typing import Any, Protocol, TextIO

from sentinel_contracts import AuditRecord


class AuditUnavailable(Exception):
    """An audit record could not be written."""


class AuditSink(Protocol):
    def record(self, event: AuditRecord) -> None:
        """Store one record, or raise an exception if that is not possible."""
        ...


class JsonLinesAuditSink:
    """Writes each record as one line of JSON, to standard output unless told otherwise."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream
        self._lock = threading.Lock()

    def record(self, event: AuditRecord) -> None:
        line = event.model_dump_json()
        with self._lock:
            stream = self._stream or sys.stdout
            stream.write(line + "\n")
            stream.flush()


class InMemoryAuditSink:
    """Keeps records in a list. Used by tests and local experiments."""

    def __init__(self) -> None:
        self._events: list[AuditRecord] = []
        self._lock = threading.Lock()

    def record(self, event: AuditRecord) -> None:
        with self._lock:
            self._events.append(event)

    @property
    def events(self) -> list[AuditRecord]:
        with self._lock:
            return list(self._events)

    def for_correlation(self, correlation_id: str) -> list[AuditRecord]:
        return [
            event for event in self.events if event.correlation_id == correlation_id
        ]


def sink_ready(sink: Any) -> bool:
    """Ask a sink whether it can write now. A sink without ``ready()`` always can."""
    ready = getattr(sink, "ready", None)
    return bool(ready()) if callable(ready) else True


def close_sink(sink: Any) -> None:
    """Release a sink's connections, if it has any."""
    close = getattr(sink, "close", None)
    if callable(close):
        close()
