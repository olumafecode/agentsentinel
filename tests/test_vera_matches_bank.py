"""Vera's tool schemas and scripted scenarios agree with the bank, the gateway and the seed."""

import pytest

from banking_agent.scenarios import load_scenarios
from banking_agent.tools import tool_schemas
from demo_bank_api.seed import generate
from demo_bank_api.tools import TOOLS
from sentinel_gateway.registry import AgentRegistry

BANK = generate()
SCENARIOS = load_scenarios()
SCRIPTED_CALLS = [
    pytest.param(call, id=f"{scenario.id} turn {n} {call.tool_name}")
    for scenario in SCENARIOS
    for n, turn in enumerate(scenario.turns, start=1)
    for call in turn.calls
]
UPDATE_HINT = (
    "copy the entry from the bank's GET /v1/tools into "
    "apps/banking-agent/src/banking_agent/data/tools.json"
)


def test_vera_offers_exactly_the_tools_the_gateway_allows_her():
    vera = AgentRegistry.load().get("AGT-001")

    assert [tool["name"] for tool in tool_schemas()] == list(vera.allowed_tools)


@pytest.mark.parametrize("tool", tool_schemas(), ids=lambda tool: tool["name"])
def test_each_tool_schema_matches_the_bank_catalogue(tool):
    bank = TOOLS[tool["name"]].catalogue_entry()

    assert tool["description"] == bank["description"], UPDATE_HINT
    assert tool["high_impact"] == bank["high_impact"], UPDATE_HINT
    assert tool["sensitive_parameters"] == bank["sensitive_parameters"], UPDATE_HINT
    assert tool["parameters"] == bank["arguments_schema"], UPDATE_HINT


@pytest.mark.parametrize("call", SCRIPTED_CALLS)
def test_each_scripted_call_is_a_real_tool_with_valid_arguments(call):
    spec = TOOLS[call.tool_name]

    spec.arguments_model.model_validate(call.arguments)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.id)
def test_each_scenario_customer_exists_in_the_seeded_bank(scenario):
    assert scenario.session.customer_id in BANK.customers
