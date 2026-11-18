"""The registries of agents and tools that ship with the gateway."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from sentinel_gateway.registry import (
    AgentProfile,
    AgentRegistry,
    AgentStatus,
    ToolProfile,
    ToolRegistry,
)


def test_vera_is_registered_and_active():
    vera = AgentRegistry.load().get("AGT-001")

    assert vera.name == "Vera"
    assert vera.status is AgentStatus.ACTIVE
    assert "issue_refund" in vera.allowed_tools


def test_every_tool_the_bank_offers_is_known():
    tools = ToolRegistry.load()

    assert len(tools) == 9
    assert tools["issue_refund"].high_impact is True
    assert tools["issue_refund"].sensitive_parameters == ("account_id", "amount")
    assert "wire_transfer" not in tools


def test_an_agents_status_can_change_while_the_gateway_runs():
    registry = AgentRegistry.load()

    updated = registry.set_status("AGT-001", AgentStatus.QUARANTINED)

    assert updated.status is AgentStatus.QUARANTINED
    assert registry.get("AGT-001").status is AgentStatus.QUARANTINED
    assert registry.get("AGT-001").name == "Vera"


def test_an_unknown_agent_is_not_found():
    assert AgentRegistry.load().get("AGT-999") is None


def test_each_agent_and_tool_may_be_listed_only_once():
    vera = AgentRegistry.load().get("AGT-001")
    refund = ToolRegistry.load()["issue_refund"]

    with pytest.raises(ValueError, match="listed twice"):
        AgentRegistry([vera, vera])
    with pytest.raises(ValueError, match="listed twice"):
        ToolRegistry([refund, refund])


def test_an_agents_thresholds_must_be_in_order():
    with pytest.raises(ValidationError, match="review_threshold"):
        AgentProfile(
            agent_id="AGT-009",
            name="Odd",
            role="customer_service",
            allowed_tools=("get_customer",),
            status="active",
            review_threshold=0.9,
            block_threshold=0.5,
            created_at=datetime(2026, 1, 5, tzinfo=UTC),
        )


def test_a_tool_entry_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ToolProfile(
            tool_name="get_customer",
            category="read",
            description="Read a customer",
            high_impact=False,
            sensitive_parameters=(),
            allowed_task_types=("account_inquiry",),
            owner="ops",
        )
