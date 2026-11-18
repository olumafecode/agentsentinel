"""The demo bank's data and tools match the synthetic schema and its examples."""

import json
from pathlib import Path

import pytest

from data.synthetic import models
from demo_bank_api.seed import generate
from demo_bank_api.tools import TOOLS, IssueRefundArguments, ToolCategory

EXAMPLES = json.loads(
    (
        Path(__file__).resolve().parents[1] / "data" / "synthetic" / "examples.json"
    ).read_text(encoding="utf-8")
)
BANK = generate()


@pytest.mark.parametrize(
    ("records", "schema"),
    [
        (BANK.customers, models.Customer),
        (BANK.accounts, models.Account),
        (BANK.transactions, models.Transaction),
    ],
)
def test_every_seeded_record_is_valid_synthetic_data(records, schema):
    for record in records.values():
        schema.model_validate(record.model_dump(mode="json"))


@pytest.mark.parametrize(
    ("name", "records", "key"),
    [
        ("Customer", BANK.customers, "customer_id"),
        ("Account", BANK.accounts, "account_id"),
        ("Transaction", BANK.transactions, "transaction_id"),
    ],
)
def test_schema_examples_are_real_records_in_the_bank(name, records, key):
    example = models.ENTITIES[name].model_validate(EXAMPLES[name])
    seeded = models.ENTITIES[name].model_validate(
        records[EXAMPLES[name][key]].model_dump(mode="json")
    )
    assert seeded == example


def test_the_example_refund_call_has_valid_bank_arguments():
    IssueRefundArguments.model_validate(EXAMPLES["ToolCall"]["arguments"])


def test_tool_categories_match_the_schema():
    assert {c.value for c in ToolCategory} == {c.value for c in models.ToolCategory}


def test_the_refund_tool_matches_the_example_tool_definition():
    example = EXAMPLES["ToolDefinition"]
    tool = TOOLS[example["tool_name"]]
    assert tool.category.value == example["category"]
    assert tool.description == example["description"]
    assert tool.high_impact == example["high_impact"]
    assert list(tool.sensitive_parameters) == example["sensitive_parameters"]


def test_every_tool_the_example_agent_may_use_exists():
    assert set(EXAMPLES["Agent"]["allowed_tools"]) <= set(TOOLS)
