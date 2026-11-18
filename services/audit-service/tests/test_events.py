"""The audit hash rule and event IDs."""

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from sentinel_audit.events import (
    GENESIS_HASH,
    MAX_POSITION,
    StoredEvent,
    event_hash,
    event_id_for,
    timestamp_text,
)

EXAMPLES = json.loads(
    (
        Path(__file__).resolve().parents[3] / "data" / "synthetic" / "examples.json"
    ).read_text(encoding="utf-8")
)


def test_the_schema_example_hashes_to_its_stored_hash():
    example = EXAMPLES["AuditEvent"]
    event = StoredEvent(
        position=1,
        **{
            **example,
            "created_at": datetime.fromisoformat(example["created_at"]),
        },
    )

    assert event.fields() == example
    assert event.computed_hash() == example["event_hash"]
    assert event.previous_event_hash == GENESIS_HASH


def test_the_hash_ignores_only_event_hash():
    fields = {"event_id": "EVT-000001", "payload": {"b": 1, "a": "é"}}

    assert event_hash(fields) == event_hash({**fields, "event_hash": "x" * 64})
    assert event_hash(fields) != event_hash({**fields, "payload": {"b": 2, "a": "é"}})


@pytest.mark.parametrize(
    ("moment", "text"),
    [
        (datetime(2026, 3, 14, 15, 2, 11, tzinfo=UTC), "2026-03-14T15:02:11Z"),
        (
            datetime(2026, 3, 14, 15, 2, 11, 5, tzinfo=UTC),
            "2026-03-14T15:02:11.000005Z",
        ),
        (
            datetime(2026, 3, 14, 9, 2, 11, tzinfo=timezone(timedelta(hours=-6))),
            "2026-03-14T15:02:11Z",
        ),
        (datetime(2026, 3, 14, 15, 2, 11), "2026-03-14T15:02:11Z"),  # noqa: DTZ001
    ],
)
def test_times_are_written_in_utc_with_a_z(moment, text):
    assert timestamp_text(moment) == text


def test_event_ids_follow_the_chain_position():
    assert event_id_for(1) == "EVT-000001"
    assert event_id_for(MAX_POSITION) == "EVT-999999"
    with pytest.raises(ValueError, match="at most"):
        event_id_for(MAX_POSITION + 1)
    with pytest.raises(ValueError):
        event_id_for(0)
