"""The gateway's registries agree with the demo bank's catalogue and the synthetic schema."""

import json
import re
from pathlib import Path

import pytest

from data.synthetic import models
from demo_bank_api.tools import TOOLS
from sentinel_gateway.registry import (
    AgentRegistry,
    AgentStatus,
    ToolCategory,
    ToolRegistry,
)
from sentinel_gateway.scope import RECORD_PATTERNS

GATEWAY_TOOLS = ToolRegistry.load()
GATEWAY_AGENTS = AgentRegistry.load()
EXAMPLES = json.loads(
    (
        Path(__file__).resolve().parents[1] / "data" / "synthetic" / "examples.json"
    ).read_text(encoding="utf-8")
)


def test_the_gateway_knows_exactly_the_tools_the_bank_offers():
    assert set(GATEWAY_TOOLS) == set(TOOLS)


@pytest.mark.parametrize("tool_name", sorted(TOOLS))
def test_each_tool_is_described_the_same_way_in_both_places(tool_name):
    gateway, bank = GATEWAY_TOOLS[tool_name], TOOLS[tool_name]
    assert gateway.category.value == bank.category.value
    assert gateway.description == bank.description
    assert gateway.high_impact == bank.high_impact
    assert gateway.sensitive_parameters == bank.sensitive_parameters


@pytest.mark.parametrize("tool_name", sorted(TOOLS))
def test_each_tool_entry_is_a_valid_tool_definition(tool_name):
    models.ToolDefinition.model_validate(
        GATEWAY_TOOLS[tool_name].model_dump(mode="json")
    )


def test_the_example_tool_definition_matches_the_registry():
    example = models.ToolDefinition.model_validate(EXAMPLES["ToolDefinition"])
    entry = GATEWAY_TOOLS[example.tool_name].model_dump(mode="json")
    assert models.ToolDefinition.model_validate(entry) == example


def test_every_registered_agent_is_a_valid_agent_using_known_tools():
    for agent_id in GATEWAY_AGENTS.ids():
        agent = GATEWAY_AGENTS.get(agent_id)
        models.Agent.model_validate(agent.model_dump(mode="json"))
        assert set(agent.allowed_tools) <= set(GATEWAY_TOOLS)


def test_vera_matches_the_example_agent():
    example = models.Agent.model_validate(EXAMPLES["Agent"])
    vera = models.Agent.model_validate(
        GATEWAY_AGENTS.get(example.agent_id).model_dump(mode="json")
    )
    assert vera == example


@pytest.mark.parametrize(
    ("gateway_enum", "schema_enum"),
    [(AgentStatus, models.AgentStatus), (ToolCategory, models.ToolCategory)],
)
def test_registry_values_match_the_schema(gateway_enum, schema_enum):
    assert {m.value for m in gateway_enum} == {m.value for m in schema_enum}


@pytest.mark.parametrize("tool_name", sorted(TOOLS))
def test_every_record_id_a_tool_takes_is_checked_for_customer_scope(tool_name):
    """A new kind of record ID (a card number, say) must be added to the scope check."""
    properties = (
        TOOLS[tool_name].arguments_model.model_json_schema().get("properties", {})
    )
    id_patterns = {
        spec["pattern"]
        for spec in properties.values()
        if re.match(r"^\^[A-Z]{3}-", spec.get("pattern", ""))
    }
    assert id_patterns <= {pattern.pattern for pattern in RECORD_PATTERNS.values()}
