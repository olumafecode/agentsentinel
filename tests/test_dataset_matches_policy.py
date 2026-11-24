"""Every label in the dataset agrees with the live bank policy in OPA (US-21, US-02a).

Each event goes to a real OPA server with the bank's policies, exactly as the gateway
would send it. For every rule the policy has, the policy must report it for an event
if and only if the labeller's check of the same name failed for that event. Rules
the policy does not have yet (R1 for other customers' records, R4, R5, R7 and R8)
are not compared here; the gateway, US-02b and US-04 cover them.

Needs the opa command: skipped on a developer's machine without it, and failing in
CI (root conftest.py).
"""

import re
from pathlib import Path

import httpx2
import pytest

from data.synthetic.dataset.generator import AGENT_ID, generate
from data.synthetic.dataset.sources import Sources
from sentinel_gateway.policy import DECISION_PATH
from sentinel_gateway.registry import ToolRegistry

ROOT = Path(__file__).resolve().parents[1]
POLICY_RULES = frozenset(
    name
    for path in sorted((ROOT / "policies" / "opa").rglob("*.rego"))
    if not path.name.endswith("_test.rego")
    for name in re.findall(r'"rule":\s*"([a-z_]+)"', path.read_text("utf-8"))
)
"""Every rule name the bank policy can report."""


@pytest.fixture(scope="module")
def dataset():
    return generate()


@pytest.fixture(scope="module")
def answers(opa_url, dataset):
    """OPA's violations for every event, built the way the gateway builds its input."""
    agent = Sources.load(dataset.seed).agents[AGENT_ID]
    tools = ToolRegistry.load()
    found = {}
    with httpx2.Client(base_url=opa_url, timeout=10) as client:
        for event in dataset.events:
            call = event.row["tool_call"]
            tool = tools[call["tool_name"]]
            document = {
                "agent": {
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "allowed_tools": list(agent.allowed_tools),
                },
                "tool": {
                    "tool_name": tool.tool_name,
                    "category": tool.category.value,
                    "high_impact": tool.high_impact,
                    "sensitive_parameters": list(tool.sensitive_parameters),
                },
                "action": {
                    key: call[key]
                    for key in (
                        "task_type",
                        "tool_name",
                        "customer_scope",
                        "arguments",
                        "provenance_labels",
                    )
                },
            }
            response = client.post(DECISION_PATH, json={"input": document})
            response.raise_for_status()
            found[event.event_id] = response.json()["result"]["violations"]
    return found


def test_the_policy_reports_exactly_the_labellers_checks_it_shares(dataset, answers):
    disagreements = []
    for event in dataset.events:
        reported = {violation["rule"] for violation in answers[event.event_id]}
        expected = set(event.label.checks) & POLICY_RULES
        if reported != expected:
            disagreements.append((event.event_id, sorted(reported), sorted(expected)))

    assert disagreements == []


def test_the_policy_never_blocks_an_action_the_labels_allow(dataset, answers):
    for event in dataset.events:
        if any(v["decision"] == "BLOCK" for v in answers[event.event_id]):
            assert event.row["expected_outcome"] in ("BLOCK", "QUARANTINE")


def test_the_dataset_has_an_example_of_every_policy_rule(dataset):
    checks = {check for event in dataset.events for check in event.label.checks}

    assert POLICY_RULES - checks == {"incomplete_input"}
