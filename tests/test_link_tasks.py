"""tools/board/link_tasks.py fills in planning-table issue links only when every row checks out."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = json.loads(
    (ROOT / "tools" / "board" / "backlog.json").read_text(encoding="utf-8")
)
AGREEMENT = (ROOT / "docs" / "agile" / "working-agreement.md").read_text(
    encoding="utf-8"
)
SPRINT_2_PLANNING = (
    ROOT / "docs" / "agile" / "sprints" / "sprint-2" / "planning.md"
).read_text(encoding="utf-8")
REPO_URL = "https://github.com/olumafecode/agentsentinel"

spec = importlib.util.spec_from_file_location(
    "link_tasks", ROOT / "tools" / "board" / "link_tasks.py"
)
link_tasks = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = link_tasks  # dataclasses look their module up here
spec.loader.exec_module(link_tasks)

TEAM = link_tasks.people(AGREEMENT)
TITLES = link_tasks.task_titles(BACKLOG)
US_02A = [task for task in TITLES if task.startswith("US-02a.")]


def board_state(tasks, first=133):
    """A state file as plan-sprint leaves it, with consecutive issue numbers."""
    return {
        "issues": {
            f"task:{task}": {"number": n, "url": f"{REPO_URL}/issues/{n}"}
            for n, task in enumerate(tasks, first)
        }
    }


def table(tasks, ref="#___", owner="Olusanya Mafe"):
    lines = ["| Story | Task | Owner | Week |", "|---|---|---|---|"]
    for task in tasks:
        story = task.rsplit(".", 1)[0]
        lines.append(f"| {story} | {ref} {task} {TITLES[task]} | {owner} | 1 |")
    return (
        "# Planning\n\nSome text about #___ and US-02a.1.\n\n" + "\n".join(lines) + "\n"
    )


def test_the_working_agreement_gives_each_person_their_github_username():
    assert TEAM == {"Siyabonga Jali": "siyabonga169", "Olusanya Mafe": "olumafecode"}


def test_each_placeholder_becomes_a_link_to_its_task_issue():
    result = link_tasks.fill(table(US_02A), board_state(US_02A), BACKLOG, TEAM)

    assert result.errors == [] and result.unplanned == []
    assert result.filled == len(US_02A)
    assert f"| US-02a | [#133]({REPO_URL}/issues/133) US-02a.1 " in result.text
    assert f"| US-02a | [#137]({REPO_URL}/issues/137) US-02a.5 " in result.text
    assert "Some text about #___ and US-02a.1." in result.text


def test_a_second_run_changes_nothing():
    first = link_tasks.fill(table(US_02A), board_state(US_02A), BACKLOG, TEAM)
    second = link_tasks.fill(first.text, board_state(US_02A), BACKLOG, TEAM)

    assert second.errors == [] and second.filled == 0
    assert second.text == first.text


def test_tasks_without_an_issue_are_reported_until_plan_sprint_has_run():
    result = link_tasks.fill(table(US_02A), board_state(US_02A[:2]), BACKLOG, TEAM)

    assert result.unplanned == US_02A[2:]
    assert result.errors == []


def test_a_mistyped_title_names_the_right_one():
    text = table(US_02A).replace("Integration test AT-03", "Integration test AT-3")

    result = link_tasks.fill(text, board_state(US_02A), BACKLOG, TEAM)

    assert any(
        "US-02a.5 should be 'Integration test AT-03'" in e for e in result.errors
    )


def test_a_task_under_the_wrong_story_is_reported():
    text = table(US_02A).replace("| US-02a | #___ US-02a.3", "| US-02b | #___ US-02a.3")

    result = link_tasks.fill(text, board_state(US_02A), BACKLOG, TEAM)

    assert any("US-02a.3 belongs to US-02a, not US-02b" in e for e in result.errors)


def test_an_owner_outside_the_working_agreement_is_reported():
    result = link_tasks.fill(
        table(US_02A, owner="Olu Mafe"), board_state(US_02A), BACKLOG, TEAM
    )

    assert any(
        "owner 'Olu Mafe' is not in the working agreement" in e for e in result.errors
    )


def test_a_story_with_a_missing_or_repeated_task_is_reported():
    tasks = [*US_02A[:-1], US_02A[0]]

    result = link_tasks.fill(table(tasks), board_state(US_02A), BACKLOG, TEAM)

    assert "US-02a.1 is listed 2 times" in result.errors
    assert "US-02a is missing tasks: US-02a.5" in result.errors


def test_a_filled_in_link_to_the_wrong_issue_is_reported():
    filled = link_tasks.fill(table(US_02A), board_state(US_02A), BACKLOG, TEAM).text
    wrong = filled.replace(
        f"[#135]({REPO_URL}/issues/135)", f"[#136]({REPO_URL}/issues/136)"
    )

    result = link_tasks.fill(wrong, board_state(US_02A), BACKLOG, TEAM)

    assert any(
        "US-02a.3 links to #136, but its issue is #135" in e for e in result.errors
    )


def test_a_task_cell_that_cannot_be_read_is_reported():
    text = table(US_02A).replace("#___ US-02a.2", "#__ US-02a.2")

    result = link_tasks.fill(text, board_state(US_02A), BACKLOG, TEAM)

    assert any("cannot read the task cell" in e for e in result.errors)
    assert "US-02a is missing tasks: US-02a.2" in result.errors


def test_the_sprint_2_plan_lists_every_sprint_2_task_with_its_backlog_title():
    sprint_2 = [
        f"{story['id']}.{n}"
        for story in BACKLOG["stories"]
        if story["sprint"] == "Sprint 2"
        for n in range(1, len(story["tasks"]) + 1)
    ]

    result = link_tasks.fill(SPRINT_2_PLANNING, {"issues": {}}, BACKLOG, TEAM)

    assert result.errors == []
    assert sorted(row.task for row in result.rows) == sorted(sprint_2)


def test_the_command_writes_nothing_while_any_row_is_wrong(tmp_path, capsys):
    planning = tmp_path / "planning.md"
    original = table(US_02A, owner="Nobody")
    planning.write_text(original, encoding="utf-8")
    state = tmp_path / "state.json"
    state.write_text(json.dumps(board_state(US_02A)), encoding="utf-8")

    code = link_tasks.main(["--repo", "o/r", str(planning), "--state", str(state)])

    assert code == 1
    assert planning.read_text(encoding="utf-8") == original
    assert "Nothing was changed." in capsys.readouterr().out


def test_the_command_fills_the_links_and_keeps_windows_line_endings(tmp_path):
    planning = tmp_path / "planning.md"
    planning.write_bytes(table(US_02A).replace("\n", "\r\n").encode("utf-8"))
    state = tmp_path / "state.json"
    state.write_text(json.dumps(board_state(US_02A)), encoding="utf-8")
    command = ["--repo", "o/r", str(planning), "--state", str(state)]

    assert link_tasks.main([*command, "--check"]) == 1
    assert link_tasks.main(command) == 0
    assert link_tasks.main([*command, "--check"]) == 0

    written = planning.read_bytes()
    assert f"[#133]({REPO_URL}/issues/133)".encode() in written
    assert b"\r\n" in written and b"\n" not in written.replace(b"\r\n", b"")


def test_assign_gives_each_task_issue_to_its_owner(monkeypatch):
    calls = []

    def run(command, **_):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(link_tasks.shutil, "which", lambda _: "gh")
    monkeypatch.setattr(link_tasks.subprocess, "run", run)
    text = (
        table(US_02A[:1], owner="Siyabonga Jali")
        + table(US_02A[1:]).split("\n\n", 2)[2]
    )
    result = link_tasks.fill(text, board_state(US_02A), BACKLOG, TEAM)

    failures = link_tasks.assign(result.rows, board_state(US_02A), TEAM, "o/r")

    assert failures == 0
    assert calls[0] == [
        "gh",
        "issue",
        "edit",
        "133",
        "--repo",
        "o/r",
        "--add-assignee",
        "siyabonga169",
    ]
    assert calls[1] == [
        "gh",
        "issue",
        "edit",
        "134",
        "--repo",
        "o/r",
        "--add-assignee",
        "olumafecode",
    ]
    assert len(calls) == len(US_02A)


@pytest.mark.parametrize("returncode, failures", [(0, 0), (1, 5)])
def test_assign_counts_the_issues_it_could_not_assign(
    monkeypatch, returncode, failures
):
    monkeypatch.setattr(link_tasks.shutil, "which", lambda _: "gh")
    monkeypatch.setattr(
        link_tasks.subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(
            command, returncode, "", "no such user"
        ),
    )
    rows = link_tasks.fill(table(US_02A), board_state(US_02A), BACKLOG, TEAM).rows

    assert link_tasks.assign(rows, board_state(US_02A), TEAM, "o/r") == failures
