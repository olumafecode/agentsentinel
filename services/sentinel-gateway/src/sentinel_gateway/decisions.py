"""Idempotent decisions by correlation ID (US-18.5, NFR-03).

The first request with a correlation ID is evaluated and, if allowed, executed. Its
outcome is kept, and a repeat of the same request gets the same outcome back without
being evaluated or executed again, so an agent that retries after a timeout cannot
cause a second refund. A different request that reuses the correlation ID is refused.

Two identical requests that arrive together are handled one after the other: the
second waits for the first and then receives its outcome.

The record is in memory, per process, and is kept for an hour. Requests older than
five minutes are refused anyway (RequestFreshnessCheck), so an expired record can
never be repeated. A gateway with more than one replica must move this record to
PostgreSQL first (ADR-012).
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from sentinel_contracts import ActionOutcome

DEFAULT_RETENTION_SECONDS = 60 * 60
DEFAULT_CAPACITY = 10_000


class CorrelationConflict(Exception):
    """The correlation ID was already used for a different request."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__(
            f"correlation ID {correlation_id} was already used for a different request"
        )
        self.correlation_id = correlation_id


@dataclass
class _Entry:
    fingerprint: str
    created_at: float
    lock: threading.Lock = field(default_factory=threading.Lock)
    outcome: ActionOutcome | None = None


class DecisionStore:
    """Remembers the outcome for each correlation ID."""

    def __init__(
        self,
        *,
        retention_seconds: float = DEFAULT_RETENTION_SECONDS,
        capacity: int = DEFAULT_CAPACITY,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if retention_seconds <= 0 or capacity <= 0:
            raise ValueError("retention_seconds and capacity must be positive")
        self._retention = retention_seconds
        self._capacity = capacity
        self._clock = clock
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def run_once(
        self,
        correlation_id: str,
        fingerprint: str,
        produce: Callable[[], ActionOutcome],
    ) -> tuple[ActionOutcome, bool]:
        """Return the stored outcome for this request, or produce and store a new one.

        ``fingerprint`` identifies the request: the same correlation ID with another
        fingerprint raises CorrelationConflict. The second value returned is True when
        the outcome is a stored one. If ``produce`` raises, nothing is stored and the
        request can be tried again.
        """
        while True:
            entry = self._entry_for(correlation_id, fingerprint)
            with entry.lock:
                if entry.outcome is not None:
                    return entry.outcome, True
                with self._lock:
                    still_current = self._entries.get(correlation_id) is entry
                if not still_current:
                    # An earlier attempt failed and gave up its place; start again.
                    continue
                try:
                    entry.outcome = produce()
                except BaseException:
                    with self._lock:
                        self._entries.pop(correlation_id, None)
                    raise
                return entry.outcome, False

    def _entry_for(self, correlation_id: str, fingerprint: str) -> _Entry:
        with self._lock:
            now = self._clock()
            self._evict(now)
            entry = self._entries.get(correlation_id)
            if entry is None:
                entry = _Entry(fingerprint=fingerprint, created_at=now)
                self._entries[correlation_id] = entry
            elif entry.fingerprint != fingerprint:
                raise CorrelationConflict(correlation_id)
            return entry

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def _evict(self, now: float) -> None:
        # Entries are in arrival order, so the oldest are at the front. One still
        # being produced stops the sweep; it is seconds old and finishes soon.
        while self._entries:
            correlation_id, entry = next(iter(self._entries.items()))
            expired = now - entry.created_at >= self._retention
            over_capacity = len(self._entries) >= self._capacity
            if entry.outcome is None or not (expired or over_capacity):
                return
            del self._entries[correlation_id]
