"""The bank's written policies are well formed and agree with the live policy (US-06a.1).

The explanation service cites these documents by section ID, so the IDs must be
well formed and unique, and every cross-reference must lead somewhere. The limits
and lists they state must match what the gateway enforces, or an explanation would
quote a rule that is not the one applied.
"""

import json
import re
from pathlib import Path

import pytest

from demo_bank_api.tools import TOOLS
from sentinel_contracts import ReasonCode, TaskType
from sentinel_gateway.checks import MAX_REQUEST_AGE

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data" / "policy-documents"
DOCUMENTS = {
    "AAP": FOLDER / "ai-agent-access-policy.md",
    "CDA": FOLDER / "customer-data-access-policy.md",
    "RAP": FOLDER / "refund-authorization-policy.md",
    "IRS": FOLDER / "incident-response-standard.md",
}
POLICY = json.loads(
    (ROOT / "policies" / "opa" / "agentsentinel" / "data.json").read_text("utf-8")
)
SETTINGS = POLICY["settings"]
SECTION = re.compile(r"^### ((AAP|CDA|RAP|IRS)-(\d+)\.(\d+)) (\S.*)$")
PART = re.compile(r"^## (\d+)\. (\S.*)$")
REFERENCE = re.compile(r"\b(?:AAP|CDA|RAP|IRS)-\d+\.\d+\b")
WORDS = {3: "three", 4: "four", 5: "five", 10: "ten"}
TASK_NAMES = {
    "Account inquiry": "account_inquiry",
    "Refund request": "refund_request",
    "Profile update": "profile_update",
    "Dispute": "dispute",
    "Administrative maintenance": "admin_maintenance",
}


def read(prefix):
    return DOCUMENTS[prefix].read_text("utf-8")


def raw_sections(prefix):
    """Section ID to its lines as written, in the order they appear."""
    found, current = {}, None
    for line in read(prefix).splitlines():
        heading = SECTION.match(line)
        if heading:
            current = heading.group(1)
            found[current] = []
        elif line.startswith("## "):
            current = None
        elif current:
            found[current].append(line)
    return {section_id: "\n".join(lines) for section_id, lines in found.items()}


def sections(prefix):
    """Section ID to its text on one line, for searching."""
    return {sid: " ".join(text.split()) for sid, text in raw_sections(prefix).items()}


ALL_RAW = {
    sid: text for prefix in DOCUMENTS for sid, text in raw_sections(prefix).items()
}
ALL_SECTIONS = {sid: " ".join(text.split()) for sid, text in ALL_RAW.items()}


def money(cents):
    return f"{cents // 100:,}.{cents % 100:02d}"


def cents(text):
    whole, _, fraction = text.partition(".")
    return int(whole) * 100 + int(fraction.ljust(2, "0"))


@pytest.mark.parametrize("prefix", sorted(DOCUMENTS))
def test_each_document_names_its_id_and_version(prefix):
    text = read(prefix)

    assert f"| Document ID | {prefix} |" in text
    assert re.search(r"^\| Version \| \d+\.\d+ \|$", text, re.MULTILINE)
    assert "Veridane is a fictional bank." in text


@pytest.mark.parametrize("prefix", sorted(DOCUMENTS))
def test_sections_are_numbered_in_order_under_their_part(prefix):
    part, last = None, None
    for line in read(prefix).splitlines():
        heading = PART.match(line)
        if heading:
            part, last = int(heading.group(1)), 0
            continue
        section = SECTION.match(line)
        if line.startswith("### "):
            assert section, f"{prefix}: a section heading without a valid ID: {line}"
            assert section.group(2) == prefix
            assert int(section.group(3)) == part, (
                f"{section.group(1)} is under part {part}"
            )
            assert int(section.group(4)) == last + 1, (
                f"{section.group(1)} is out of order"
            )
            last += 1


@pytest.mark.parametrize("prefix", sorted(DOCUMENTS))
def test_every_section_has_text(prefix):
    for section_id, text in sections(prefix).items():
        assert len(text) >= 40, f"{section_id} is empty or too short to cite"


def test_every_cross_reference_names_a_section_that_exists():
    for prefix in DOCUMENTS:
        for reference in REFERENCE.findall(read(prefix)):
            assert reference in ALL_SECTIONS, f"{prefix} refers to {reference}"


def test_every_section_the_readme_names_exists():
    readme = (FOLDER / "README.md").read_text("utf-8")

    named = set(REFERENCE.findall(readme))
    assert named, "the README names no sections"
    assert named <= set(ALL_SECTIONS), sorted(named - set(ALL_SECTIONS))


def test_every_reason_code_but_within_policy_has_sections_to_cite():
    readme = (FOLDER / "README.md").read_text("utf-8")
    rows = re.findall(r"^\| `([A-Z_]+)` \| [^|]+ \| ([^|]+) \|$", readme, re.MULTILINE)

    assert {code for code, _ in rows} == {c.value for c in ReasonCode} - {
        "WITHIN_POLICY"
    }
    for code, cited in rows:
        for section_id in (s.strip() for s in cited.split(",")):
            assert section_id in ALL_SECTIONS, f"{code} cites {section_id}"


def test_the_task_table_matches_the_live_policy():
    table = re.findall(
        r"^\| ([A-Z][a-z ]+) \| ([a-z_, ]+) \|$", ALL_RAW["AAP-3.2"], re.MULTILINE
    )
    written = {
        TASK_NAMES[task]: [tool.strip() for tool in tools.split(",")]
        for task, tools in table
    }

    assert written == POLICY["task_tools"]
    assert set(written) == {task.value for task in TaskType}


def test_the_refund_limits_match_the_live_policy():
    automatic = money(cents(SETTINGS["automatic_refund_limit"]))
    cap = money(cents(SETTINGS["refund_hard_cap"]))

    assert f"up to and including {automatic} USD" in ALL_SECTIONS["RAP-3.2"]
    assert f"above {automatic} USD and up to {cap} USD" in ALL_SECTIONS["RAP-3.3"]
    assert f"above {cap} USD is never issued" in ALL_SECTIONS["RAP-3.4"]


def test_the_refund_patterns_match_the_live_policy():
    burst = SETTINGS["refund_burst"]
    near = SETTINGS["near_limit"]

    assert (
        f"more than {WORDS[burst['more_than']]} refunds within "
        f"{WORDS[burst['window_minutes']]} minutes"
    ) in ALL_SECTIONS["RAP-6.1"]
    assert (
        f"between {near['band_from']} and {near['band_to']} USD"
        in ALL_SECTIONS["RAP-6.2"]
    )
    assert f"within {near['window_hours']} hours" in ALL_SECTIONS["RAP-6.2"]
    assert "second or later" in ALL_SECTIONS["RAP-6.2"]
    assert near["refunds"] == 2


def test_the_quarantine_trigger_matches_the_live_policy():
    quarantine = SETTINGS["quarantine"]
    trigger = (
        f"{WORDS[quarantine['blocked_actions']]} actions blocked within "
        f"{WORDS[quarantine['window_minutes']]} minutes"
    )

    assert trigger in ALL_SECTIONS["IRS-3.1"]
    assert trigger in ALL_SECTIONS["AAP-6.3"]


def test_the_freshness_window_matches_the_gateway():
    minutes = int(MAX_REQUEST_AGE.total_seconds() // 60)

    assert f"within {WORDS[minutes]} minutes" in ALL_SECTIONS["AAP-4.2"]


def test_the_transaction_history_limit_matches_the_bank():
    largest = TOOLS["get_transactions"].arguments_model.model_fields["limit"]
    (maximum,) = [m.le for m in largest.metadata if hasattr(m, "le")]

    assert f"at most the {maximum} most recent transactions" in ALL_SECTIONS["CDA-3.2"]


def test_the_tools_named_in_the_policies_exist():
    named = set(re.findall(r"\b[a-z]+_[a-z_]+\b", ALL_RAW["AAP-3.2"]))

    assert named <= set(TOOLS)
