"""The dataset's files: the splits, the manifest and the review sample (US-21).

Each split is a JSON Lines file: one event per line, keys sorted, no spaces, UTF-8,
and a "\\n" after every line. Written this way the bytes, and so the SHA-256
checksums, are the same on every operating system and Python version.

manifest.json is committed; the split files are not. The manifest records the seed,
the generator version and the checksum of every split. Anyone can rebuild the files
from the seed, write_splits() refuses to write data that does not match the
manifest, and read_split() refuses a file whose checksum is not the manifest's. So
the frozen test set cannot change without anyone noticing.
"""

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from data.synthetic.dataset.generator import (
    GENERATOR_VERSION,
    Dataset,
    Event,
    balance,
)
from data.synthetic.dataset.rng import Rng
from data.synthetic.models import (
    SCHEMA_VERSION,
    DatasetSplit,
    Decision,
    FailureMode,
    LabelledActionEvent,
)

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.json"
REVIEW_SAMPLE = HERE / "review-sample.md"
OUTPUT = HERE / "output"
"""Where the split files are written by default. Git ignores this folder."""

NAME = "agentsentinel-labelled-actions"
RULES = tuple(f"R{number}" for number in range(1, 10))
REVIEW_QUOTA = {**{rule: 5 for rule in RULES[:-1]}, "R9": 10}
"""Events per rule in the review sample: 5 for each of R1 to R8, 10 allowed (R9)."""


REVIEW_HEADER = """\
# Review sample for dataset {version}

Task US-21.2 (#154): the Product Owner checks these labelled events by hand against \
[the labelling rules](../labelling-rules.md).

The sample has {count} events, drawn at random from all three splits by the \
generator's review stream: {quota}. A plain random sample of 50 would hold about 30 \
allowed events and could miss a rule altogether, so the draw is made rule by rule.

How to review:

1. For each row, read the action and work out the outcome, rule and failure mode \
from the labelling rules before you look at the label columns.
2. Write Yes or No under Agree. For No, write what you expected under Note.
3. R5, R7 and R8 depend on earlier actions in the same session. Those sessions are \
listed in full after the table.
4. A disagreement is fixed in the rules or the generator, and a new dataset version \
is frozen. Labels are never edited by hand.

| # | Event | Session | Time (UTC) | Customer | Task | Tool | Arguments | Untrusted \
| Outcome | Rule | Failure mode | Why (labeller) | Agree | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
"""


class DatasetMismatch(Exception):
    """The data does not match the frozen manifest."""


# ------------------------------------------------------------------ the splits
def file_name(split: DatasetSplit) -> str:
    return f"{split.value}.jsonl"


def jsonl(events: Iterable[Event]) -> bytes:
    lines = (
        json.dumps(dict(event.row), sort_keys=True, separators=(",", ":")) + "\n"
        for event in events
    )
    return "".join(lines).encode("utf-8")


def write_splits(dataset: Dataset, directory: Path = OUTPUT) -> dict[str, Path]:
    """Write the three split files, once the data is known to match the manifest."""
    verify(dataset)
    directory.mkdir(parents=True, exist_ok=True)
    written = {}
    for split in DatasetSplit:
        path = directory / file_name(split)
        path.write_bytes(jsonl(dataset.split(split)))
        written[split.value] = path
    return written


def read_split(
    split: DatasetSplit, directory: Path = OUTPUT, manifest_file: Path = MANIFEST
) -> list[LabelledActionEvent]:
    """Read one split file, after checking it is the one the manifest froze."""
    path = directory / file_name(split)
    content = path.read_bytes()
    expected = load_manifest(manifest_file)["splits"][split.value]["sha256"]
    if hashlib.sha256(content).hexdigest() != expected:
        raise DatasetMismatch(
            f"{path} is not the frozen {split.value} split. Rebuild it with "
            "'py -m data.synthetic.dataset write'."
        )
    return [
        LabelledActionEvent.model_validate_json(line)
        for line in content.decode("utf-8").splitlines()
    ]


# ------------------------------------------------------------------ the manifest
def manifest(dataset: Dataset) -> dict[str, Any]:
    """The manifest for a dataset, as freeze writes it."""
    splits = {}
    for split in DatasetSplit:
        events = dataset.split(split)
        splits[split.value] = {
            "file": file_name(split),
            "rows": len(events),
            "sequences": len({event.sequence_id for event in events}),
            "sha256": hashlib.sha256(jsonl(events)).hexdigest(),
            "expected_outcome": _counts(events, "expected_outcome", Decision),
            "failure_mode": _counts(events, "failure_mode", FailureMode),
            "rule": _counts(events, "rule", RULES),
        }
    return {
        "name": NAME,
        "generator_version": GENERATOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "policy_version": dataset.policy_version,
        "seed": dataset.seed,
        "rows": len(dataset.events),
        "sequences": len({event.sequence_id for event in dataset.events}),
        "splits": splits,
    }


def load_manifest(manifest_file: Path = MANIFEST) -> dict[str, Any]:
    return json.loads(manifest_file.read_text(encoding="utf-8"))


def differences(dataset: Dataset, frozen: Mapping[str, Any]) -> list[str]:
    """How the dataset differs from a frozen manifest; empty if it is the same data.

    policy_version is not compared: it records which policy bundle the labels were
    frozen with. A policy change that changes any label changes the checksums.
    """
    built = manifest(dataset)
    found = [
        f"{key} is {built[key]!r}, the manifest says {frozen.get(key)!r}"
        for key in ("name", "generator_version", "schema_version", "seed")
        if built[key] != frozen.get(key)
    ]
    for split, entry in built["splits"].items():
        if entry != frozen.get("splits", {}).get(split):
            found.append(f"the {split} split is not the frozen one")
    return found


def verify(dataset: Dataset, manifest_file: Path = MANIFEST) -> None:
    if not manifest_file.exists():
        raise DatasetMismatch(f"{manifest_file} does not exist yet: run freeze first")
    found = differences(dataset, load_manifest(manifest_file))
    if found:
        raise DatasetMismatch(
            "The generated data does not match the frozen manifest: "
            + "; ".join(found)
            + ". If the change is intended, bump GENERATOR_VERSION in "
            "data/synthetic/dataset/generator.py and run freeze."
        )


def freeze(
    dataset: Dataset,
    manifest_file: Path = MANIFEST,
    review_file: Path = REVIEW_SAMPLE,
) -> bool:
    """Record a new dataset version. Returns False if it is already frozen.

    A version is frozen once: the same version with different data is refused,
    because the test set of a frozen version must never change.
    """
    if manifest_file.exists():
        frozen = load_manifest(manifest_file)
        if frozen.get("generator_version") == GENERATOR_VERSION:
            found = differences(dataset, frozen)
            if not found:
                return False
            raise DatasetMismatch(
                f"Version {GENERATOR_VERSION} is already frozen with different data ("
                + "; ".join(found)
                + "). Bump GENERATOR_VERSION in data/synthetic/dataset/generator.py."
            )
    manifest_file.write_text(
        json.dumps(manifest(dataset), indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    review_file.write_text(review_sample(dataset), encoding="utf-8", newline="\n")
    return True


def _counts(
    events: Sequence[Event], field: str, values: Iterable[Any]
) -> dict[str, int]:
    counted = balance(events, field)
    return {
        str(getattr(value, "value", value)): counted[getattr(value, "value", value)]
        for value in values
    }


# ------------------------------------------------------------- the review sample
def review_events(dataset: Dataset) -> list[Event]:
    """The events for the Product Owner's hand check (US-21.2), in time order."""
    rng = Rng(dataset.seed, "review")
    chosen: list[Event] = []
    for rule in RULES:
        pool = [event for event in dataset.events if event.row["rule"] == rule]
        chosen.extend(rng.shuffled(pool)[: REVIEW_QUOTA[rule]])
    return sorted(chosen, key=lambda event: event.event_id)


def review_sample(dataset: Dataset) -> str:
    sample = review_events(dataset)
    quota = ", ".join(f"{count} for {rule}" for rule, count in REVIEW_QUOTA.items())
    lines = REVIEW_HEADER.format(
        version=GENERATOR_VERSION, count=len(sample), quota=quota
    ).splitlines()
    for number, event in enumerate(sample, start=1):
        call = event.row["tool_call"]
        cells = [
            str(number),
            event.event_id,
            f"{event.sequence_id} #{event.row['position']}",
            call["requested_at"],
            call["customer_scope"],
            call["task_type"],
            call["tool_name"],
            _code(call["arguments"]),
            _untrusted(call),
            event.row["expected_outcome"],
            event.row["rule"],
            event.row["failure_mode"],
            event.label.reason,
            "",
            "",
        ]
        lines.append(_row(cells))

    lines += [
        "",
        "## Sessions behind the R5, R7 and R8 events",
        "",
    ]
    for event in sample:
        if event.row["rule"] not in ("R5", "R7", "R8"):
            continue
        lines += [
            f"### {event.sequence_id}, for {event.event_id} ({event.row['rule']})",
            "",
            "| # | Time (UTC) | Tool | Arguments | Untrusted | Outcome | Rule |",
            "|---|---|---|---|---|---|---|",
        ]
        for step in dataset.sequence(event.sequence_id):
            call = step.row["tool_call"]
            lines.append(
                _row(
                    [
                        str(step.row["position"]),
                        call["requested_at"],
                        call["tool_name"],
                        _code(call["arguments"]),
                        _untrusted(call),
                        step.row["expected_outcome"],
                        step.row["rule"],
                    ]
                )
            )
        lines.append("")
    lines += [
        "## Result",
        "",
        "- Reviewed by:",
        "- Date:",
        f"- Events agreed: ___ of {len(sample)}",
        "",
    ]
    return "\n".join(lines)


def _row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |"


def _code(arguments: Mapping[str, Any]) -> str:
    return "`" + json.dumps(arguments, separators=(", ", ": ")) + "`"


def _untrusted(call: Mapping[str, Any]) -> str:
    names = [
        name
        for name, origin in call["provenance_labels"].items()
        if origin == "untrusted_content"
    ]
    return ", ".join(names) if names else "none"
