"""Finding broken links in the hash chain (US-19.3)."""

from dataclasses import replace
from datetime import UTC, datetime

from sentinel_audit.events import GENESIS_HASH, StoredEvent, event_hash, event_id_for
from sentinel_audit.verify import verify_chain


def chain(length):
    events = []
    previous = GENESIS_HASH
    for position in range(1, length + 1):
        fields = {
            "event_id": event_id_for(position),
            "correlation_id": "3f2b8c1e-5a7d-4e9b-9c1a-2d4f6a8b0c1e",
            "event_type": "decision_made",
            "actor": "sentinel-gateway",
            "decision": "BLOCK",
            "policy_version": None,
            "model_version": None,
            "payload": {"reason_codes": ["UNKNOWN_TOOL"], "n": position},
            "created_at": "2027-01-15T08:00:00Z",
            "previous_event_hash": previous,
        }
        digest = event_hash(fields)
        events.append(
            StoredEvent(
                position=position,
                **{**fields, "created_at": datetime(2027, 1, 15, 8, tzinfo=UTC)},
                event_hash=digest,
            )
        )
        previous = digest
    return events


def test_an_untouched_chain_is_intact():
    events = chain(5)

    report = verify_chain(events)

    assert report.intact
    assert report.checked == 5
    assert report.last_hash == events[-1].event_hash


def test_an_empty_chain_is_intact():
    report = verify_chain([])

    assert report.intact
    assert report.last_hash == GENESIS_HASH


def test_a_changed_event_no_longer_matches_its_hash():
    events = chain(4)
    events[1] = replace(events[1], payload={"reason_codes": ["WITHIN_POLICY"], "n": 2})

    report = verify_chain(events)

    assert report.problems == (
        (
            "EVT-000002: event_hash does not match its content; the event was "
            "changed after it was written"
        ),
    )


def test_rehashing_a_changed_event_breaks_the_next_link():
    events = chain(4)
    changed = replace(events[1], decision="ALLOW")
    events[1] = replace(changed, event_hash=changed.computed_hash())

    report = verify_chain(events)

    assert report.problems == (
        "EVT-000003: previous_event_hash does not match the event before it",
    )


def test_a_deleted_event_is_found():
    events = chain(4)
    del events[1]

    report = verify_chain(events)

    assert not report.intact
    assert report.problems[0].startswith("EVT-000003: expected EVT-000002")
    assert "EVT-000003: previous_event_hash does not match" in report.problems[1]


def test_an_event_id_that_does_not_match_its_position_is_found():
    events = chain(2)
    events[1] = replace(events[1], event_id="EVT-000007")

    report = verify_chain(events)

    assert any("does not match its position 2" in p for p in report.problems)
