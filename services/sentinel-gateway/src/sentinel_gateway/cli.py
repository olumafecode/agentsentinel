"""Command line for the gateway.

python -m sentinel_gateway issue-session   Sign a customer session token for local tests
python -m sentinel_gateway new-key         Print a random key for the gateway's settings

In the real flow the identity service issues session tokens when a customer signs in.
issue-session stands in for it on a developer's machine and in the scenario runner.
"""

import argparse
import os
import secrets
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from sentinel_contracts import TaskType, TokenError, issue_session_token, load_key
from sentinel_contracts.session_token import MAX_SESSION_TTL_SECONDS


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m sentinel_gateway", description=__doc__
    )
    commands = parser.add_subparsers(dest="command", required=True)

    session = commands.add_parser(
        "issue-session", help="sign a customer session token with SESSION_TOKEN_KEY"
    )
    session.add_argument(
        "--customer", required=True, help="customer ID, such as CUS-000123"
    )
    session.add_argument(
        "--task",
        required=True,
        choices=[task.value for task in TaskType],
        help="what the customer asked for",
    )
    session.add_argument(
        "--agent", default="AGT-001", help="agent ID (default: AGT-001)"
    )
    session.add_argument(
        "--session", help="session ID, such as SES-00000042 (default: a random one)"
    )
    session.add_argument("--channel", default="web_chat", help="default: web_chat")
    session.add_argument(
        "--minutes",
        type=int,
        default=30,
        help=f"how long the session lasts, 1 to {MAX_SESSION_TTL_SECONDS // 60} (default: 30)",
    )

    commands.add_parser(
        "new-key",
        help="print a random key for EXECUTION_TOKEN_KEY, SESSION_TOKEN_KEY or AGENT_KEYS",
    )

    args = parser.parse_args(argv)
    if args.command == "new-key":
        print(secrets.token_urlsafe(48))
        return 0
    return _issue_session(args)


def _issue_session(args: argparse.Namespace) -> int:
    secret = os.environ.get("SESSION_TOKEN_KEY")
    if not secret:
        print("SESSION_TOKEN_KEY is not set in this terminal.", file=sys.stderr)
        return 2
    session_id = args.session or f"SES-{secrets.randbelow(10**8):08d}"
    try:
        token = issue_session_token(
            key=load_key(secret),
            session_id=session_id,
            customer_id=args.customer,
            agent_id=args.agent,
            task_type=args.task,
            channel=args.channel,
            ttl_seconds=args.minutes * 60,
        )
    except (TokenError, ValidationError, ValueError) as exc:
        print(f"Could not issue the session token: {exc}", file=sys.stderr)
        return 2
    print(token)
    print(
        f"Session {session_id} for {args.customer} ({args.task}), "
        f"agent {args.agent}, valid for {args.minutes} minutes.",
        file=sys.stderr,
    )
    return 0
