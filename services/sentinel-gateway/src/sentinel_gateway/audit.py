"""Where the gateway sends its audit records (FR-13, NFR-06).

Every evaluated action produces action_received, decision_made and then either
action_executed or action_stopped. The audit service in US-19 will store them in a
hash chain; until it exists, JsonLinesAuditSink writes each record as one line of
JSON to standard output, where Docker and Kubernetes collect it.

If either of the first two records cannot be written, the gateway refuses the action
rather than run it unaudited.
"""

import sys
import threading
from typing import Protocol, TextIO

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
