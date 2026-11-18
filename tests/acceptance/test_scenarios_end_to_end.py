"""Vera's active scenarios, end to end: Vera, the gateway and the bank together (US-17, US-26).

Every active scenario must pass against the real services, and every action Vera
proposed must leave a complete audit trail (US-19.5).
"""

import pytest

from banking_agent.scenarios import load_scenarios, run_scenario
from sentinel_audit.completeness import check_completeness

ACTIVE = [scenario for scenario in load_scenarios() if scenario.status == "active"]


@pytest.mark.parametrize("scenario", ACTIVE, ids=lambda scenario: scenario.id)
def test_each_active_scenario_passes_against_the_real_services(stack, scenario):
    vera, identity = stack.vera()

    result = run_scenario(scenario, vera, identity)

    assert result.status == "passed", result.problems
    report = check_completeness(
        stack.audit.events, expected=result.conversation.correlation_ids()
    )
    assert report.ok, report.incomplete


def test_blocked_scenario_actions_never_reach_a_bank_tool(stack):
    vera, identity = stack.vera()
    blocked = [s for s in ACTIVE if s.id in {"UC-04", "UC-05"}]

    for scenario in blocked:
        run_scenario(scenario, vera, identity)

    tool_calls = [
        r.url.path for r in stack.bank_requests if r.url.path.startswith("/v1/tools/")
    ]
    assert tool_calls == ["/v1/tools/get_transactions"]
