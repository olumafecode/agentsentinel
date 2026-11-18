"""Command line for Vera's scripted scenarios (US-17.3).

python -m banking_agent list                     Show every scenario and its status
python -m banking_agent run                      Run every active scenario
python -m banking_agent run UC-01 UC-04          Run only these
python -m banking_agent run --include-pending    Also run scenarios still waiting on a story

Vera reads GATEWAY_URL and VERA_AGENT_KEY. The runner also plays the customer's
sign-in, so it needs SESSION_TOKEN_KEY; Vera herself never receives it. The exit code
is 1 when an active scenario fails, so CI can run the scenarios after deployment.
"""

import argparse
import os
import sys
from collections.abc import Sequence

from banking_agent.agent import Vera
from banking_agent.config import ConfigError, VeraSettings
from banking_agent.gateway import GatewayClient
from banking_agent.identity import IdentityStandIn
from banking_agent.scenarios import (
    Scenario,
    ScenarioResult,
    load_scenarios,
    run_scenario,
)
from sentinel_contracts import TokenError, load_key


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m banking_agent", description=__doc__
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="show every scenario and its status")
    run = commands.add_parser("run", help="run scenarios through the gateway")
    run.add_argument(
        "ids", nargs="*", metavar="UC-NN", help="scenarios to run (default: all)"
    )
    run.add_argument(
        "--include-pending",
        action="store_true",
        help="also run scenarios that wait on a story; their results do not fail the run",
    )

    args = parser.parse_args(argv)
    scenarios = load_scenarios()
    if args.command == "list":
        for scenario in scenarios:
            print(f"{scenario.id}  {_status(scenario):<22} {scenario.title}")
        return 0
    return _run(scenarios, args.ids, args.include_pending)


def _run(scenarios: list[Scenario], ids: list[str], include_pending: bool) -> int:
    unknown = sorted(set(ids) - {scenario.id for scenario in scenarios})
    if unknown:
        print(f"Unknown scenario(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    try:
        settings = VeraSettings.from_env()
        identity = IdentityStandIn(load_key(os.environ.get("SESSION_TOKEN_KEY", "")))
    except (ConfigError, TokenError) as exc:
        print(f"Cannot run the scenarios: {exc}", file=sys.stderr)
        print("Set GATEWAY_URL, VERA_AGENT_KEY and SESSION_TOKEN_KEY.", file=sys.stderr)
        return 2

    chosen = [s for s in scenarios if not ids or s.id in ids]
    gateway = GatewayClient(
        settings.gateway_url,
        settings.agent_key,
        timeout_seconds=settings.timeout_seconds,
    )
    vera = Vera(gateway, agent_id=settings.agent_id)
    counts = {"passed": 0, "failed": 0, "pending": 0}
    try:
        for scenario in chosen:
            if scenario.status == "pending" and not include_pending:
                print(
                    f"{scenario.id} {scenario.title}: PENDING, waits on {scenario.pending_on}\n"
                )
                counts["pending"] += 1
                continue
            result = run_scenario(scenario, vera, identity)
            counts[result.status] += 1
            _print(result)
    finally:
        gateway.close()

    print(
        f"{counts['passed']} passed, {counts['failed']} failed, {counts['pending']} pending"
    )
    return 1 if counts["failed"] else 0


def _status(scenario: Scenario) -> str:
    return (
        "active" if scenario.status == "active" else f"pending ({scenario.pending_on})"
    )


def _print(result: ScenarioResult) -> None:
    scenario = result.scenario
    label = result.status.upper()
    if result.status == "pending":
        label = f"PENDING, waits on {scenario.pending_on}"
    print(f"{scenario.id} {scenario.title}: {label}")
    for turn in result.conversation.turns:
        print(f"  Customer: {turn.message}")
        for proposal in turn.proposals:
            if proposal.outcome is None:
                print(f"    {proposal.call.tool_name}: no decision ({proposal.error})")
                continue
            decision = proposal.outcome.decision
            reasons = ", ".join(decision.reason_codes)
            print(
                f"    {proposal.call.tool_name}: {decision.decision} ({reasons}) "
                f"[{proposal.correlation_id}]"
            )
        for call in turn.not_proposed:
            print(f"    {call.tool_name}: not proposed")
        if turn.reply:
            print(f"  Vera: {turn.reply}")
    for problem in result.problems:
        print(f"  ! {problem}")
    print()
