"""Command line for the demo bank.

python -m demo_bank_api reset       Return a running bank to its seeded state
python -m demo_bank_api seed-info   Show what the seed produces, without a server
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence

from demo_bank_api.seed import DEFAULT_SEED
from demo_bank_api.store import BankStore

DEFAULT_URL = "http://localhost:8001"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m demo_bank_api", description=__doc__
    )
    commands = parser.add_subparsers(dest="command", required=True)

    reset = commands.add_parser(
        "reset", help="return a running bank to its seeded state"
    )
    reset.add_argument(
        "--url",
        default=os.environ.get("BANK_URL", DEFAULT_URL),
        help=f"bank address (default: BANK_URL or {DEFAULT_URL})",
    )

    info = commands.add_parser(
        "seed-info", help="show record counts and the seeded checksum"
    )
    info.add_argument(
        "--seed", type=int, default=int(os.environ.get("BANK_SEED", DEFAULT_SEED))
    )

    args = parser.parse_args(argv)
    if args.command == "reset":
        return _reset(args.url)
    return _seed_info(args.seed)


def _reset(url: str) -> int:
    if not url.startswith(("http://", "https://")):
        print("The bank address must start with http:// or https://", file=sys.stderr)
        return 2
    admin_key = os.environ.get("DEMO_ADMIN_KEY")
    if not admin_key:
        print("DEMO_ADMIN_KEY is not set in this terminal.", file=sys.stderr)
        return 2
    request = urllib.request.Request(
        f"{url.rstrip('/')}/admin/reset",
        method="POST",
        headers={"X-Admin-Key": admin_key},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(json.dumps(json.load(response), indent=2))
            return 0
    except urllib.error.HTTPError as exc:
        print(
            f"The bank refused the reset (HTTP {exc.code}): {exc.read().decode()}",
            file=sys.stderr,
        )
    except urllib.error.URLError as exc:
        print(f"Could not reach the bank at {url}: {exc.reason}", file=sys.stderr)
    return 1


def _seed_info(seed: int) -> int:
    store = BankStore(seed=seed)
    print(
        json.dumps(
            {"seed": seed, **store.counts(), "checksum": store.checksum()}, indent=2
        )
    )
    return 0
