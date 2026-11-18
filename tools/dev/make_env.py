"""Write a .env file with random values for every setting in .env.example (US-20).

Run from the repository root:  py tools/dev/make_env.py
It refuses to replace an existing .env unless you pass --force.
"""

import argparse
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETTING = re.compile(r"^([A-Z][A-Z0-9_]*)=")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="replace an existing .env")
    parser.add_argument(
        "--output", type=Path, default=ROOT / ".env", help="default: .env"
    )
    args = parser.parse_args(argv)

    if args.output.exists() and not args.force:
        print(
            f"{args.output} already exists. Pass --force to replace it.",
            file=sys.stderr,
        )
        return 1
    lines = []
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        match = SETTING.match(line)
        lines.append(f"{match.group(1)}={secrets.token_urlsafe(32)}" if match else line)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} with new random values. Keep it out of git.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
