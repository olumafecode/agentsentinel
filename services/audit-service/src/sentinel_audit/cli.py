"""Command line for the audit trail.

python -m sentinel_audit migrate        Create or update the audit schema and the gateway's role
python -m sentinel_audit verify-chain   Check every link in the hash chain
python -m sentinel_audit completeness   Check that every action has a complete trail

migrate reads AUDIT_ADMIN_DATABASE_URL and AUDIT_GATEWAY_DB_PASSWORD. The other two
read AUDIT_DATABASE_URL and need only read access. Each exits with 1 when it finds a
problem, so CI and scripts can rely on the exit code.
"""

import argparse
import os
import sys
from collections.abc import Sequence

import psycopg

from sentinel_audit.completeness import check_completeness
from sentinel_audit.migrate import migrate
from sentinel_audit.store import AuditStore
from sentinel_audit.verify import verify_chain


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m sentinel_audit", description=__doc__
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="create or update the audit schema and role")
    verify = commands.add_parser("verify-chain", help="check every link in the chain")
    complete = commands.add_parser(
        "completeness", help="check that every action has a complete trail"
    )
    complete.add_argument(
        "--correlation-id",
        action="append",
        default=[],
        metavar="ID",
        help="an action that must be present; repeat for several",
    )
    for command in (verify, complete):
        command.add_argument(
            "--database-url",
            default=os.environ.get("AUDIT_DATABASE_URL"),
            help="default: AUDIT_DATABASE_URL",
        )

    args = parser.parse_args(argv)
    try:
        if args.command == "migrate":
            return _migrate()
        if not args.database_url:
            print("AUDIT_DATABASE_URL is not set in this terminal.", file=sys.stderr)
            return 2
        store = AuditStore.connect(args.database_url, max_connections=1, wait=True)
        try:
            if args.command == "verify-chain":
                return _verify(store)
            return _completeness(store, args.correlation_id)
        finally:
            store.close()
    except psycopg.Error as exc:
        print(f"The database refused or could not be reached: {exc}", file=sys.stderr)
        return 2


def _migrate() -> int:
    admin_url = os.environ.get("AUDIT_ADMIN_DATABASE_URL")
    password = os.environ.get("AUDIT_GATEWAY_DB_PASSWORD")
    if not admin_url or not password:
        print(
            "AUDIT_ADMIN_DATABASE_URL and AUDIT_GATEWAY_DB_PASSWORD must both be set.",
            file=sys.stderr,
        )
        return 2
    try:
        applied = migrate(admin_url, password)
    except ValueError as exc:
        print(f"Cannot migrate: {exc}", file=sys.stderr)
        return 2
    if applied:
        print(f"Applied {len(applied)} migration(s): {', '.join(applied)}")
    else:
        print("The audit schema is already up to date.")
    return 0


def _verify(store: AuditStore) -> int:
    report = verify_chain(store.events())
    if report.intact:
        print(f"Checked {report.checked} events: the chain is intact.")
        print(f"Latest hash: {report.last_hash}")
        return 0
    print(f"Checked {report.checked} events: the chain is broken.")
    for problem in report.problems:
        print(f"  {problem}")
    return 1


def _completeness(store: AuditStore, expected: list[str]) -> int:
    report = check_completeness(store.events(), expected=expected)
    print(
        f"{report.actions} actions, {report.complete} with a complete audit trail "
        f"({report.ratio:.1%})."
    )
    for trail in report.incomplete:
        print(f"  {trail.correlation_id}: {'; '.join(trail.problems)}")
    return 0 if report.ok else 1
