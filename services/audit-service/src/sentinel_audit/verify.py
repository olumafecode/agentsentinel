"""Checking the hash chain (US-19.3).

Every event must carry the next event ID, point at the hash of the event before it,
and hash to its own event_hash. A row changed or deleted directly in the database
breaks at least one of these.

The chain cannot show that events were removed from its end: the remaining events
still link up. The database refuses deletes (US-19.4); publishing the latest hash
somewhere outside the database would close that gap later.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from sentinel_audit.events import GENESIS_HASH, StoredEvent, event_id_for


@dataclass(frozen=True)
class ChainReport:
    checked: int
    problems: tuple[str, ...]
    last_hash: str

    @property
    def intact(self) -> bool:
        return not self.problems


def verify_chain(events: Iterable[StoredEvent]) -> ChainReport:
    """Check events in chain order and describe every broken link."""
    problems: list[str] = []
    previous_hash = GENESIS_HASH
    expected_position = 1
    checked = 0
    for event in events:
        checked += 1
        if event.position != expected_position:
            problems.append(
                f"{event.event_id}: expected {event_id_for(expected_position)} at this "
                "point; an event is missing or out of order"
            )
        if event.event_id != event_id_for(event.position):
            problems.append(
                f"{event.event_id}: the event ID does not match its position "
                f"{event.position}"
            )
        if event.previous_event_hash != previous_hash:
            problems.append(
                f"{event.event_id}: previous_event_hash does not match the event "
                "before it"
            )
        if event.computed_hash() != event.event_hash:
            problems.append(
                f"{event.event_id}: event_hash does not match its content; the event "
                "was changed after it was written"
            )
        previous_hash = event.event_hash
        expected_position = event.position + 1
    return ChainReport(
        checked=checked, problems=tuple(problems), last_hash=previous_hash
    )
