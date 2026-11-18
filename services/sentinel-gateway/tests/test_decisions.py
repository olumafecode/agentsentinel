"""The correlation ID record behind idempotent decisions (US-18.5)."""

import threading
import uuid
from datetime import UTC, datetime

import pytest

from sentinel_contracts import ActionOutcome, Decision, GovernanceDecision, ReasonCode
from sentinel_gateway.decisions import CorrelationConflict, DecisionStore


class Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


def outcome(correlation_id):
    return ActionOutcome(
        decision=GovernanceDecision(
            correlation_id=correlation_id,
            decision=Decision.BLOCK,
            reason_codes=[ReasonCode.UNKNOWN_TOOL],
            summary="Blocked.",
            decided_at=datetime(2027, 1, 15, tzinfo=UTC),
        )
    )


class Producer:
    """Counts how often the store asked for a new outcome."""

    def __init__(self, correlation_id):
        self.correlation_id = correlation_id
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return outcome(self.correlation_id)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def store(clock):
    return DecisionStore(retention_seconds=60, capacity=3, clock=clock)


def new_id():
    return str(uuid.uuid4())


def test_the_first_request_is_produced_and_repeats_are_served_from_the_store(store):
    cid = new_id()
    produce = Producer(cid)

    first, first_replayed = store.run_once(cid, "fp", produce)
    second, second_replayed = store.run_once(cid, "fp", produce)

    assert (first_replayed, second_replayed) == (False, True)
    assert second is first
    assert produce.calls == 1


def test_a_different_fingerprint_for_a_known_id_is_a_conflict(store):
    cid = new_id()
    store.run_once(cid, "fp", Producer(cid))

    with pytest.raises(CorrelationConflict) as caught:
        store.run_once(cid, "another", Producer(cid))
    assert caught.value.correlation_id == cid


def test_nothing_is_kept_when_producing_fails(store):
    cid = new_id()

    def explode():
        raise RuntimeError("audit down")

    with pytest.raises(RuntimeError):
        store.run_once(cid, "fp", explode)
    assert len(store) == 0

    _, replayed = store.run_once(cid, "another", Producer(cid))
    assert replayed is False


def test_a_waiting_duplicate_takes_over_when_the_first_attempt_fails(store):
    cid = new_id()
    started = threading.Event()
    release = threading.Event()
    results = []

    def failing():
        started.set()
        release.wait(timeout=5)
        raise RuntimeError("audit down")

    def first():
        with pytest.raises(RuntimeError):
            store.run_once(cid, "fp", failing)

    thread = threading.Thread(target=first)
    thread.start()
    assert started.wait(timeout=5)
    produce = Producer(cid)
    waiter = threading.Thread(
        target=lambda: results.append(store.run_once(cid, "fp", produce))
    )
    waiter.start()
    release.set()
    thread.join(timeout=5)
    waiter.join(timeout=5)

    assert produce.calls == 1
    assert results[0][1] is False
    assert store.run_once(cid, "fp", produce)[1] is True
    assert produce.calls == 1


def test_outcomes_are_forgotten_after_the_retention_period(store, clock):
    cid = new_id()
    store.run_once(cid, "fp", Producer(cid))
    clock.now += 60

    store.run_once(new_id(), "fp", Producer(cid))

    assert len(store) == 1
    _, replayed = store.run_once(cid, "fp", Producer(cid))
    assert replayed is False


def test_the_oldest_outcomes_make_room_when_the_store_is_full(store):
    ids = [new_id() for _ in range(4)]
    for cid in ids:
        store.run_once(cid, "fp", Producer(cid))

    assert len(store) == 3
    assert store.run_once(ids[-1], "fp", Producer(ids[-1]))[1] is True
    assert store.run_once(ids[0], "fp", Producer(ids[0]))[1] is False


@pytest.mark.parametrize("kwargs", [{"retention_seconds": 0}, {"capacity": 0}])
def test_retention_and_capacity_must_be_positive(kwargs):
    with pytest.raises(ValueError):
        DecisionStore(**kwargs)
