"""The labelled synthetic action dataset meets US-21's acceptance criteria.

- The generator and its fixed seed give the same dataset and checksums every run,
  and those are the checksums frozen in manifest.json.
- Train, validation and test are 70/15/15, and no session is split between them.
- Every split holds normal behavior and every failure mode in proposal Section 2.1.

The other tests check what the dataset card and the labelling rules promise.
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

import pytest

from data.synthetic.dataset import __main__ as cli
from data.synthetic.dataset.files import (
    REVIEW_QUOTA,
    REVIEW_SAMPLE,
    DatasetMismatch,
    differences,
    freeze,
    jsonl,
    load_manifest,
    manifest,
    read_split,
    review_events,
    write_splits,
)
from data.synthetic.dataset.generator import GENERATOR_VERSION, PLAN, SEED, generate
from data.synthetic.dataset.scenarios import FAMILIES
from data.synthetic.dataset.sources import Bank, BankPolicy, is_attacker_account
from data.synthetic.models import (
    SCHEMA_VERSION,
    DatasetSplit,
    Decision,
    FailureMode,
    LabelledActionEvent,
)
from demo_bank_api.seed import DEFAULT_SEED, WINDOW_END, WINDOW_START

ROOT = Path(__file__).resolve().parents[1]
CARD = (ROOT / "data" / "synthetic" / "dataset" / "README.md").read_text("utf-8")
TARGET = {"ALLOW": 60, "HUMAN_REVIEW": 12, "BLOCK": 22, "QUARANTINE": 6}
"""The class balance to aim for, in percent (labelling-rules.md)."""
SHARES = {"train": 0.70, "validation": 0.15, "test": 0.15}
OUTCOME_OF_RULE = {
    "R1": "BLOCK",
    "R2": "BLOCK",
    "R3": "BLOCK",
    "R4": "BLOCK",
    "R5": "QUARANTINE",
    "R6": "HUMAN_REVIEW",
    "R7": "BLOCK",
    "R8": "HUMAN_REVIEW",
    "R9": "ALLOW",
}
RULES_OF_FAILURE = {
    "none": {"R6", "R9"},
    "prompt_injection": {"R1", "R4"},
    "misunderstood_instruction": {"R2"},
    "wrong_tool_or_invalid_details": {"R2", "R3"},
    "outside_authority": {"R1"},
    "unintended_sequence": {"R1", "R2", "R5", "R7", "R8", "R9"},
}
"""Where each failure mode's actions land (dataset card). R9 under a failure mode is
an action of the failure that is still allowed, such as the start of a burst."""


@pytest.fixture(scope="module")
def dataset():
    return generate()


@pytest.fixture(scope="module")
def rows(dataset):
    return [event.row for event in dataset.events]


def sessions(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["sequence_id"]].append(row)
    return grouped


def at(row):
    return datetime.fromisoformat(row["tool_call"]["requested_at"])


# ------------------------------------------------------------ acceptance criteria
def test_the_same_seed_gives_the_same_dataset_and_checksums(dataset):
    again = generate()

    assert manifest(again) == manifest(dataset)
    for split in DatasetSplit:
        assert jsonl(again.split(split)) == jsonl(dataset.split(split))


def test_the_generated_data_is_the_frozen_data(dataset):
    assert differences(dataset, load_manifest()) == []


def test_the_manifest_records_the_seed_versions_and_a_checksum_per_split():
    frozen = load_manifest()

    assert frozen["seed"] == SEED == DEFAULT_SEED == 20261109
    assert frozen["generator_version"] == GENERATOR_VERSION
    assert frozen["schema_version"] == SCHEMA_VERSION
    assert re.fullmatch(r"\d+\.\d+\.\d+", frozen["policy_version"])
    assert set(frozen["splits"]) == {split.value for split in DatasetSplit}
    for entry in frozen["splits"].values():
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
    assert sum(e["rows"] for e in frozen["splits"].values()) == frozen["rows"]


def test_the_splits_are_70_15_15(dataset, rows):
    total_sessions = len(sessions(rows))
    for split in DatasetSplit:
        events = dataset.split(split)
        share = len(events) / len(rows)
        session_share = len({e.sequence_id for e in events}) / total_sessions

        assert share == pytest.approx(SHARES[split.value], abs=0.015)
        assert session_share == pytest.approx(SHARES[split.value], abs=0.01)


def test_no_session_is_split_between_two_parts(rows):
    for sequence_id, session in sessions(rows).items():
        assert len({row["split"] for row in session}) == 1, sequence_id


@pytest.mark.parametrize("split", [split.value for split in DatasetSplit])
def test_every_split_holds_normal_behavior_and_every_failure_mode(rows, split):
    in_split = [row for row in rows if row["split"] == split]

    assert {row["failure_mode"] for row in in_split} == {m.value for m in FailureMode}
    assert {row["expected_outcome"] for row in in_split} == {d.value for d in Decision}
    assert {row["rule"] for row in in_split} == set(OUTCOME_OF_RULE)


def test_every_family_has_sessions_in_every_split(dataset):
    for family in FAMILIES:
        splits = {e.split for e in dataset.events if e.family == family}
        assert splits == set(DatasetSplit), family


# --------------------------------------------------------- the rows themselves
def test_the_size_is_within_the_story_range(rows):
    assert 2000 <= len(rows) <= 5000


def test_every_row_matches_the_schema(rows):
    for row in rows:
        LabelledActionEvent.model_validate(row)


def test_identifiers_are_unique_and_sessions_are_in_order(rows):
    assert [row["event_id"] for row in rows] == [
        f"EVT-{n:06d}" for n in range(1, len(rows) + 1)
    ]
    assert len({row["tool_call"]["correlation_id"] for row in rows}) == len(rows)
    for session in sessions(rows).values():
        assert [row["position"] for row in session] == list(range(1, len(session) + 1))
        assert [at(row) for row in session] == sorted(at(row) for row in session)
        for field in ("session_id", "agent_id", "customer_scope", "task_type"):
            assert len({row["tool_call"][field] for row in session}) == 1


def test_every_outcome_is_the_one_its_rule_gives(rows):
    for row in rows:
        assert row["expected_outcome"] == OUTCOME_OF_RULE[row["rule"]]


def test_failure_modes_land_where_the_dataset_card_says(rows):
    landed = defaultdict(set)
    for row in rows:
        landed[row["failure_mode"]].add(row["rule"])

    assert dict(landed) == RULES_OF_FAILURE


def test_the_class_balance_is_close_to_the_target(rows):
    counted = Counter(row["expected_outcome"] for row in rows)
    for outcome, percent in TARGET.items():
        assert 100 * counted[outcome] / len(rows) == pytest.approx(percent, abs=2)


def test_times_are_inside_the_synthetic_data_window(rows):
    for row in rows:
        assert WINDOW_START <= at(row) <= WINDOW_END


def test_sessions_stand_alone(rows):
    policy = BankPolicy.load()
    gap = max(policy.quarantine_window, policy.refund_burst_window)
    ordered = sorted(sessions(rows).values(), key=lambda s: at(s[0]))
    last_seen = {}
    for previous, current in pairwise(ordered):
        assert at(current[0]) - at(previous[-1]) > gap
    for session in ordered:
        customer = session[0]["tool_call"]["customer_scope"]
        if customer in last_seen:
            assert at(session[0]) - last_seen[customer] > policy.near_limit_window
        last_seen[customer] = at(session[-1])


def test_refunds_that_can_go_ahead_never_exceed_the_purchase(rows):
    bank = Bank(SEED)
    for session in sessions(rows).values():
        refunded = Counter()
        for row in session:
            call = row["tool_call"]
            if call["tool_name"] == "issue_refund" and row["rule"] in {
                "R6",
                "R8",
                "R9",
            }:
                purchase = call["arguments"]["original_transaction_id"]
                refunded[purchase] += Decimal(call["arguments"]["amount"])
                assert refunded[purchase] <= bank.transaction_amount(purchase)


def test_injected_refunds_outside_the_scope_go_to_attacker_accounts(dataset):
    for event in dataset.events:
        call = event.row["tool_call"]
        if event.family == "injected_refund" and event.row["rule"] == "R1":
            assert is_attacker_account(call["arguments"]["account_id"])


def test_untrusted_values_appear_only_where_a_scenario_put_them(rows):
    for row in rows:
        labels = row["tool_call"]["provenance_labels"]
        untrusted = {k for k, v in labels.items() if v == "untrusted_content"}
        if untrusted and row["failure_mode"] == "none":
            assert untrusted == {"reason"}


# ---------------------------------------------------------- the frozen files
def test_written_splits_read_back_only_while_they_match_the_manifest(dataset, tmp_path):
    write_splits(dataset, tmp_path)
    for split in DatasetSplit:
        read = read_split(split, tmp_path)
        assert [event.event_id for event in read] == [
            event.event_id for event in dataset.split(split)
        ]

    test_file = tmp_path / "test.jsonl"
    test_file.write_bytes(test_file.read_bytes().replace(b'"ALLOW"', b'"BLOCK"', 1))
    with pytest.raises(DatasetMismatch, match="not the frozen test split"):
        read_split(DatasetSplit.TEST, tmp_path)


def test_a_frozen_version_cannot_be_frozen_again_with_other_data(dataset, tmp_path):
    manifest_file = tmp_path / "manifest.json"
    review_file = tmp_path / "review-sample.md"

    assert freeze(dataset, manifest_file, review_file) is True
    assert freeze(dataset, manifest_file, review_file) is False

    changed = load_manifest(manifest_file)
    changed["splits"]["test"]["sha256"] = "0" * 64
    manifest_file.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(DatasetMismatch, match="Bump GENERATOR_VERSION"):
        freeze(dataset, manifest_file, review_file)


def test_the_committed_manifest_is_the_one_freeze_writes(dataset):
    frozen = load_manifest()
    built = manifest(dataset)
    built["policy_version"] = frozen["policy_version"]

    assert frozen == built


def test_the_split_files_are_not_committed():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "data/synthetic/dataset/output/" in ignored


# ---------------------------------------------------------- the review sample
REVIEW_ROW = re.compile(
    r"^\| (\d+) \| (EVT-\d{6}) \| (SEQ-\d{6}) #(\d+) \| [^|]+ \| (CUS-\d{6}) "
    r"\| ([a-z_]+) \| ([a-z_]+) \| .+ \| ([A-Z_]+) \| (R\d) \| ([a-z_]+) \|",
    re.MULTILINE,
)


def test_the_review_sample_lists_the_events_the_generator_draws(dataset):
    found = REVIEW_ROW.findall(REVIEW_SAMPLE.read_text(encoding="utf-8"))
    events = {event.event_id: event for event in dataset.events}
    drawn = review_events(dataset)

    assert [row[1] for row in found] == [event.event_id for event in drawn]
    assert len(found) == sum(REVIEW_QUOTA.values()) == 50
    for _, event_id, sequence_id, position, customer, task, tool, *labels in found:
        row = events[event_id].row
        assert (sequence_id, int(position)) == (row["sequence_id"], row["position"])
        assert (customer, task, tool) == (
            row["tool_call"]["customer_scope"],
            row["tool_call"]["task_type"],
            row["tool_call"]["tool_name"],
        )
        assert labels == [row["expected_outcome"], row["rule"], row["failure_mode"]]
    assert Counter(row[8] for row in found) == Counter(REVIEW_QUOTA)


def test_the_review_sample_passes_the_pre_commit_hooks_unchanged():
    text = REVIEW_SAMPLE.read_text(encoding="utf-8")

    assert not [line for line in text.splitlines() if line != line.rstrip()]
    assert text.endswith("\n") and not text.endswith("\n\n")


# ------------------------------------------------------------ the dataset card
def test_the_dataset_card_states_the_frozen_numbers():
    frozen = load_manifest()
    splits = frozen["splits"]

    assert f"| Version | {frozen['generator_version']} |" in CARD
    assert f"| Seed | {frozen['seed']} |" in CARD
    assert (
        f"| Events | {frozen['rows']:,} in {frozen['sequences']:,} sessions |" in CARD
    )
    for name, entry in splits.items():
        outcomes = " | ".join(
            f"{entry['expected_outcome'][d.value]:,}" for d in Decision
        )
        assert (
            f"| {name} | {entry['rows']:,} | {entry['sequences']:,} | {outcomes} |"
            in CARD
        ), name
        assert f"| {name} | `{entry['sha256']}` |" in CARD, name
    totals = Counter()
    for entry in splits.values():
        totals.update(entry["expected_outcome"])
    total_line = " | ".join(
        f"{totals[d.value]:,} ({100 * totals[d.value] / frozen['rows']:.1f}%)"
        for d in Decision
    )
    assert (
        f"| Total | {frozen['rows']:,} | {frozen['sequences']:,} | {total_line} |"
        in CARD
    )
    for mode in FailureMode:
        counts = [splits[s.value]["failure_mode"][mode.value] for s in DatasetSplit]
        cells = " | ".join(f"{n:,}" for n in [*counts, sum(counts)])
        assert f"| `{mode.value}` | {cells} |" in CARD, mode.value


def test_the_dataset_card_states_the_events_per_rule():
    frozen = load_manifest()
    totals = Counter()
    for entry in frozen["splits"].values():
        totals.update(entry["rule"])
    cells = " | ".join(f"{totals[rule]:,}" for rule in OUTCOME_OF_RULE)

    assert f"| Events | {cells} |" in CARD


def test_the_dataset_card_describes_every_family_with_its_sessions():
    for name, count in PLAN.items():
        family = FAMILIES[name]
        row = (
            rf"^\| `{name}` \| {count} \| [^|]+ \| {family.failure_mode.value} "
            rf"\| {family.use_case or 'none'} \| [^|]+ \|$"
        )
        assert re.search(row, CARD, re.MULTILINE), name


# ------------------------------------------------------------ the command line
def test_check_and_show_from_the_command_line(capsys):
    assert cli.main(["check"]) == 0
    assert "matches manifest.json" in capsys.readouterr().out

    assert cli.main(["show", "SEQ-000001"]) == 0
    assert "SEQ-000001" in capsys.readouterr().out

    assert cli.main(["show", "SEQ-999999"]) == 1
    assert "not in the dataset" in capsys.readouterr().err
