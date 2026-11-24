"""Command line for the labelled dataset (US-21). Run from the repository root:

    py -m data.synthetic.dataset write     rebuild the split files in the output folder
    py -m data.synthetic.dataset check     confirm the generator still gives the frozen data
    py -m data.synthetic.dataset show SEQ-000001    print one session and its labels
    py -m data.synthetic.dataset freeze    record a new version (after bumping it)

On Linux and macOS, use python in place of py.
"""

import argparse
import sys
from pathlib import Path

from data.synthetic.dataset.files import (
    OUTPUT,
    DatasetMismatch,
    freeze,
    manifest,
    verify,
    write_splits,
)
from data.synthetic.dataset.generator import GENERATOR_VERSION, Dataset, generate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="py -m data.synthetic.dataset",
        description="Build, check and freeze the labelled synthetic action dataset.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    write = commands.add_parser("write", help="write train, validation and test")
    write.add_argument("--output", type=Path, default=OUTPUT, help=f"default: {OUTPUT}")
    commands.add_parser("check", help="compare the generator with manifest.json")
    show = commands.add_parser("show", help="print one session and its labels")
    show.add_argument("sequence_id", help="for example SEQ-000001")
    commands.add_parser(
        "freeze", help="write manifest.json and review-sample.md for a new version"
    )
    args = parser.parse_args(argv)

    dataset = generate()
    try:
        if args.command == "write":
            for split, path in write_splits(dataset, args.output).items():
                print(f"{split:<10} {path}")
        elif args.command == "check":
            verify(dataset)
            built = manifest(dataset)
            print(
                f"Dataset {GENERATOR_VERSION} matches manifest.json: "
                f"{built['rows']} events in {built['sequences']} sessions."
            )
        elif args.command == "show":
            return _show(dataset, args.sequence_id)
        elif freeze(dataset):
            print(f"Froze dataset {GENERATOR_VERSION}: manifest.json, review-sample.md")
        else:
            print(f"Dataset {GENERATOR_VERSION} is already frozen with this data.")
    except DatasetMismatch as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def _show(dataset: Dataset, sequence_id: str) -> int:
    events = dataset.sequence(sequence_id)
    if not events:
        print(f"{sequence_id} is not in the dataset", file=sys.stderr)
        return 1
    first = events[0].row
    call = first["tool_call"]
    print(
        f"{sequence_id}  {events[0].family}  {call['customer_scope']}  "
        f"{call['task_type']}  split: {first['split']}"
    )
    for event in events:
        row, call = event.row, event.row["tool_call"]
        print(
            f"{row['position']:>2}  {call['requested_at']}  {call['tool_name']:<17} "
            f"{row['expected_outcome']:<12} {row['rule']}  {row['failure_mode']}"
        )
        print(f"    arguments  {call['arguments']}")
        print(f"    origin     {call['provenance_labels']}")
        print(f"    why        {event.label.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
