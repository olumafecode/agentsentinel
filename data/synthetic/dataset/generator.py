"""Build the labelled dataset from the seed (US-21).

1. PLAN says how many sessions of each family to write. Their order is shuffled.
2. Each session gets a start time on a timeline of two-hour slots from 1 July 2026,
   and a customer who is able to have that kind of session and who has not had a
   session in the previous 25 hours.
3. The family writes the session's actions. The labeller labels them in time order.
   If the agent ends a session quarantined, an administrator releases it.
4. Sessions are split 70/15/15 into train, validation and test, separately within
   each family, so every split has every kind of session. A session is never split
   between two parts.

The spacing keeps every session independent. A session starts in the first hour of
its slot and lasts at most 30 minutes, so the next one starts at least 30 minutes
after it ends: longer than the quarantine and refund-burst windows. One customer's
sessions are more than 24 hours apart, longer than the near-limit window. So R5, R7
and R8 only ever count actions from the same session.
"""

import hashlib
import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import Any

from data.synthetic.dataset.labeller import Label, Labeller
from data.synthetic.dataset.rng import Rng
from data.synthetic.dataset.scenarios import FAMILIES, Context, Family, Script
from data.synthetic.dataset.sources import Sources
from data.synthetic.models import DatasetSplit, LabelledActionEvent, ToolCall
from demo_bank_api.seed import DEFAULT_SEED, WINDOW_END

GENERATOR_VERSION = "1.0.0"
"""Bump this whenever the generated data changes, then run the freeze command."""

SEED = DEFAULT_SEED
"""The project's one seed, 20261109 (data/synthetic/README.md, rule 2)."""

AGENT_ID = "AGT-001"
"""Vera, the agent in every session."""

PLAN: Mapping[str, int] = MappingProxyType(
    {
        "inquiry": 60,
        "small_refund": 60,
        "large_refund": 235,
        "address_change": 40,
        "dispute_handling": 40,
        "injected_refund": 75,
        "injected_freeze": 25,
        "misunderstood": 75,
        "invalid_details": 95,
        "similar_tool": 35,
        "cross_customer": 85,
        "bulk_export": 45,
        "refund_burst": 50,
        "near_limit": 100,
        "admin_probe": 50,
        "repeated_violations": 60,
    }
)
"""How many sessions of each family. Chosen so the class balance comes close to the
target in labelling-rules.md; the dataset card records the actual balance."""

FIRST_SLOT = datetime(2026, 7, 1, tzinfo=UTC)
SLOT = timedelta(hours=2)
LATEST_START = timedelta(minutes=60)
"""A session starts at a random time in the first hour of its slot."""
LONGEST_SESSION = timedelta(minutes=30)
"""So a session ends at least 30 minutes before the next one starts."""
CUSTOMER_REST = timedelta(hours=25)

VALIDATION_SHARE = 0.15
TEST_SHARE = 0.15
"""Train takes the rest, 70%."""


@dataclass(frozen=True)
class Event:
    """One labelled action: the dataset row, and what the row does not keep."""

    row: Mapping[str, Any]
    label: Label
    family: str

    @property
    def event_id(self) -> str:
        return self.row["event_id"]

    @property
    def sequence_id(self) -> str:
        return self.row["sequence_id"]

    @property
    def split(self) -> DatasetSplit:
        return DatasetSplit(self.row["split"])


@dataclass(frozen=True)
class Dataset:
    seed: int
    policy_version: str
    events: tuple[Event, ...]
    """Every event, in time order."""

    def split(self, split: DatasetSplit) -> tuple[Event, ...]:
        return tuple(event for event in self.events if event.split is split)

    def sequence(self, sequence_id: str) -> tuple[Event, ...]:
        return tuple(e for e in self.events if e.sequence_id == sequence_id)


def generate(seed: int = SEED, plan: Mapping[str, int] = PLAN) -> Dataset:
    """Build the dataset. The same seed and plan always give the same dataset."""
    sources = Sources.load(seed)
    if AGENT_ID not in sources.agents:
        raise ValueError(f"{AGENT_ID} is not an active agent in the gateway registry")
    rng = Rng(seed, "events")
    labeller = Labeller(sources)
    order = rng.shuffled([name for name, count in plan.items() for _ in range(count)])
    deadline = FIRST_SLOT + SLOT * len(order)
    if deadline > WINDOW_END:
        raise ValueError(f"{len(order)} sessions do not fit before {WINDOW_END}")

    events: list[Event] = []
    last_session: dict[str, datetime] = {}
    for index, name in enumerate(order):
        family = FAMILIES[name]
        number = index + 1
        started_at = (
            FIRST_SLOT
            + SLOT * index
            + timedelta(seconds=rng.below(int(LATEST_START.total_seconds())))
        )
        customer = _customer(rng, sources, family, started_at, last_session)
        last_session[customer] = started_at
        context = Context(sources.bank, sources.policy, customer, started_at)
        script = family.build(rng, context)
        events.extend(
            _session(seed, number, family, script, context, labeller, len(events))
        )
        if labeller.is_quarantined(AGENT_ID):
            labeller.release(AGENT_ID)

    splits = _split(Rng(seed, "split"), events)
    rows = []
    for event in events:
        row = {**event.row, "split": splits[event.sequence_id].value}
        LabelledActionEvent.model_validate(row)
        rows.append(Event(MappingProxyType(row), event.label, event.family))
    return Dataset(seed, sources.policy.version, tuple(rows))


def _customer(
    rng: Rng,
    sources: Sources,
    family: Family,
    started_at: datetime,
    last_session: Mapping[str, datetime],
) -> str:
    candidates = [
        customer
        for customer in sources.bank.customers
        if started_at - last_session.get(customer, datetime.min.replace(tzinfo=UTC))
        > CUSTOMER_REST
        and family.eligible(Context(sources.bank, sources.policy, customer, started_at))
    ]
    if not candidates:
        raise ValueError(
            f"no customer can have a {family.name} session at {started_at}"
        )
    return rng.choice(candidates)


def _session(
    seed: int,
    number: int,
    family: Family,
    script: Script,
    context: Context,
    labeller: Labeller,
    events_so_far: int,
) -> list[Event]:
    sequence_id = f"SEQ-{number:06d}"
    session_id = f"SES-{number:08d}"
    at = context.started_at
    events = []
    for position, step in enumerate(script.steps, start=1):
        at += timedelta(seconds=step.pause)
        event_id = f"EVT-{events_so_far + position:06d}"
        tool_call = {
            "correlation_id": correlation_id(seed, event_id),
            "session_id": session_id,
            "agent_id": AGENT_ID,
            "customer_scope": context.customer_id,
            "task_type": script.task_type.value,
            "tool_name": step.tool_name,
            "arguments": dict(step.arguments),
            "provenance_labels": {k: v.value for k, v in step.provenance.items()},
            "requested_at": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        label = labeller.label(ToolCall.model_validate(tool_call))
        if label.rule not in step.expect:
            raise AssertionError(
                f"{sequence_id} position {position} ({family.name}, {step.tool_name}) "
                f"was labelled {label.rule}, but the scenario expects "
                f"{sorted(step.expect)}: {label.reason}"
            )
        row = {
            "event_id": event_id,
            "sequence_id": sequence_id,
            "position": position,
            "tool_call": tool_call,
            "expected_outcome": label.outcome.value,
            "failure_mode": step.failure_mode.value,
            "use_case": family.use_case,
            "rule": label.rule,
            "split": None,
        }
        events.append(Event(row, label, family.name))
    if at - context.started_at > LONGEST_SESSION:
        raise AssertionError(f"{sequence_id} lasts longer than {LONGEST_SESSION}")
    return events


def correlation_id(seed: int, event_id: str) -> str:
    """A UUID version 4 made from the seed and the event, so it is the same each run."""
    digest = hashlib.sha256(f"agentsentinel-dataset:{seed}:{event_id}".encode())
    return str(uuid.UUID(bytes=digest.digest()[:16], version=4))


def _split(rng: Rng, events: Sequence[Event]) -> dict[str, DatasetSplit]:
    """70/15/15 by session, separately within each family."""
    families: dict[str, list[str]] = {}
    for event in events:
        sequences = families.setdefault(event.family, [])
        if event.sequence_id not in sequences:
            sequences.append(event.sequence_id)
    assigned: dict[str, DatasetSplit] = {}
    for name in sorted(families):
        sequences = rng.shuffled(families[name])
        test = round(len(sequences) * TEST_SHARE)
        validation = round(len(sequences) * VALIDATION_SHARE)
        train = len(sequences) - test - validation
        for position, sequence_id in enumerate(sequences):
            if position < train:
                assigned[sequence_id] = DatasetSplit.TRAIN
            elif position < train + validation:
                assigned[sequence_id] = DatasetSplit.VALIDATION
            else:
                assigned[sequence_id] = DatasetSplit.TEST
    return assigned


def balance(events: Sequence[Event], field: str) -> Counter:
    """How many events have each value of ``field`` (expected_outcome, rule, ...)."""
    return Counter(event.row[field] for event in events)
