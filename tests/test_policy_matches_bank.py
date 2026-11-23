"""The bank policy's data agrees with the bank, the gateway and the labelling rules (US-02a).

The Rego rules are tested with ``opa test``. These tests check what the rules rely
on: that every tool and task the policy names exists, that every reason code it
returns is one the gateway knows, and that the refund settings are the ones the
dataset labels use.
"""

import json
import re
from pathlib import Path

import pytest

from demo_bank_api.tools import TOOLS
from sentinel_contracts import ReasonCode, TaskType
from sentinel_gateway.policy import Violation
from sentinel_gateway.registry import AgentRegistry

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ROOT / "policies" / "opa"
DATA = json.loads((POLICIES / "agentsentinel" / "data.json").read_text("utf-8"))
MANIFEST = json.loads((POLICIES / ".manifest").read_text("utf-8"))
RULES = [
    path
    for path in sorted(POLICIES.rglob("*.rego"))
    if not path.name.endswith("_test.rego")
]
LABELLING_RULES = (ROOT / "data" / "synthetic" / "labelling-rules.md").read_text(
    "utf-8"
)


def labelling_setting(name):
    """The value column of one row in the labelling rules' settings table."""
    match = re.search(
        rf"^\| {re.escape(name)} \| ([^|]+) \|", LABELLING_RULES, re.MULTILINE
    )
    assert match, f"{name} is missing from labelling-rules.md"
    return match.group(1).strip()


def test_the_bundle_has_a_semantic_version_and_one_root():
    assert re.fullmatch(r"\d+\.\d+\.\d+", MANIFEST["revision"])
    assert MANIFEST["roots"] == ["agentsentinel"]


def test_every_task_has_a_tool_list_and_every_listed_tool_exists():
    assert set(DATA["task_tools"]) == {task.value for task in TaskType}
    for task, tools in DATA["task_tools"].items():
        assert set(tools) <= set(TOOLS), f"{task} names a tool the bank does not have"


def test_each_of_veras_tools_is_allowed_for_at_least_one_task():
    vera = AgentRegistry.load().get("AGT-001")
    allowed = {tool for tools in DATA["task_tools"].values() for tool in tools}

    assert set(vera.allowed_tools) <= allowed


def test_the_bulk_export_tools_are_the_banks_export_tools():
    exports = {name for name, spec in TOOLS.items() if spec.category.value == "export"}

    assert set(DATA["bulk_export_tools"]) == exports


@pytest.mark.parametrize("tool_name", sorted(DATA["refund_amount_argument"]))
def test_each_refund_tool_names_a_sensitive_amount_argument(tool_name):
    spec = TOOLS[tool_name]
    argument = DATA["refund_amount_argument"][tool_name]

    assert spec.category.value == "financial"
    assert argument in spec.arguments_model.model_fields
    assert argument in spec.sensitive_parameters


def test_every_financial_tool_has_its_amount_checked():
    financial = {
        name for name, spec in TOOLS.items() if spec.category.value == "financial"
    }

    assert set(DATA["refund_amount_argument"]) == financial


@pytest.mark.parametrize(
    ("row", "value"),
    [
        ("Automatic refund limit", DATA["settings"]["automatic_refund_limit"]),
        ("Refund hard cap", DATA["settings"]["refund_hard_cap"]),
    ],
)
def test_the_refund_limits_are_the_ones_the_dataset_labels_use(row, value):
    written = labelling_setting(row).removesuffix(" USD").replace(",", "")

    assert written == value


def test_the_sequence_settings_are_the_ones_the_dataset_labels_use():
    settings = DATA["settings"]

    assert labelling_setting("Quarantine trigger") == (
        f"{settings['quarantine']['blocked_actions']} blocked actions by one agent "
        f"within {settings['quarantine']['window_minutes']} minutes"
    )
    assert labelling_setting("Refund burst") == (
        f"more than {settings['refund_burst']['more_than']} refunds by one agent "
        f"within {settings['refund_burst']['window_minutes']} minutes"
    )
    near = settings["near_limit"]
    assert labelling_setting("Near-limit refund band").startswith(
        f"{near['band_from']} to {near['band_to']} USD"
    )
    assert labelling_setting("Near-limit window") == (
        f"{near['refunds']} or more near-limit refunds for one customer "
        f"within {near['window_hours']} hours"
    )


def test_every_violation_the_rules_can_return_is_one_the_gateway_accepts():
    pattern = re.compile(
        r'"rule": "([^"]+)",\s*"decision": "([^"]+)",\s*"reason": "([^"]+)"'
    )
    found = [
        match for path in RULES for match in pattern.findall(path.read_text("utf-8"))
    ]

    assert found, "no violations found in the Rego files"
    for rule, decision, reason in found:
        Violation(rule=rule, decision=decision, reason=reason, message="A message.")
        assert ReasonCode(reason)
