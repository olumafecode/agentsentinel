"""Fill in the task issue links in a sprint's planning notes, and assign each task.

At sprint planning, `setup_board.py plan-sprint` creates the task issues. The planning
notes list the same tasks in a table, with `#___` where each issue number goes:

    | US-02a | #___ US-02a.1 Rego policies: ... | Olusanya Mafe | 1 |

This script takes each number from the board state file that plan-sprint writes, so
nobody types them by hand. It changes nothing unless every row checks out:

- the task exists on the board (plan-sprint has run for its sprint)
- the title matches tools/board/backlog.json
- the story column names the task's own story
- the owner is listed in docs/agile/working-agreement.md
- every task of every story in the table is listed exactly once
- a link that is already filled in points at the right issue

Usage (from the repository root):

    python tools/board/link_tasks.py --repo OWNER/REPO PLANNING_FILE [--check] [--assign] [--state FILE]

    --check   report only and change nothing; exits with 1 if anything is wrong or missing
    --assign  after the links are in, assign each task issue to its owner on GitHub
    --state   the board state file, if it is not the one for --repo in this folder
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BACKLOG = HERE / "backlog.json"
AGREEMENT = ROOT / "docs" / "agile" / "working-agreement.md"

PLACEHOLDER = "#___"
TASK_ID = re.compile(r"US-\d+[a-z]?\.\d+")
TASK_CELL = re.compile(
    r"(?P<ref>#___|\[#(?P<number>\d+)\]\((?P<url>[^)\s]+)\))"
    r"\s+(?P<task>US-\d+[a-z]?\.\d+)\s+(?P<title>\S.*)"
)
LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")


@dataclass(frozen=True)
class Row:
    """One task row of the planning table."""

    line: int
    story: str
    task: str
    title: str
    owner: str
    number: int | None


@dataclass(frozen=True)
class Result:
    """The planning text with the links filled in, and what was found on the way.

    `errors` are mistakes in the planning file. `unplanned` are tasks that have no
    issue yet, because plan-sprint has not run for their sprint.
    """

    text: str
    rows: list[Row]
    errors: list[str]
    unplanned: list[str]
    filled: int


def cells(line: str) -> list[str]:
    """Split a Markdown table row into its trimmed cells."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def task_titles(backlog: dict) -> dict[str, str]:
    """Every task ID in the backlog (US-02a.1 and so on) with its title."""
    return {
        f"{story['id']}.{n}": task["title"]
        for story in backlog["stories"]
        for n, task in enumerate(story["tasks"], 1)
    }


def people(agreement: str) -> dict[str, str]:
    """Each team member's name and GitHub username, from the roles table.

    Rows that name more than one person (such as "Developers") are skipped.
    """
    found: dict[str, str] = {}
    columns: tuple[int, int] | None = None
    for line in agreement.splitlines():
        if not line.lstrip().startswith("|"):
            columns = None
            continue
        row = cells(line)
        if "Person" in row and "GitHub username" in row:
            columns = (row.index("Person"), row.index("GitHub username"))
            continue
        if columns is None or len(row) <= max(columns):
            continue
        name, login = row[columns[0]], row[columns[1]]
        if "/" in name or "/" in login or not LOGIN.fullmatch(login):
            continue
        found[name] = login
    return found


def fill(text: str, state: dict, backlog: dict, team: dict[str, str]) -> Result:
    """Put each task's issue link in place of `#___`, checking every task row."""
    titles = task_titles(backlog)
    issues = state.get("issues", {})
    errors: list[str] = []
    unplanned: list[str] = []
    rows: list[Row] = []
    out: list[str] = []
    filled = 0

    for n, line in enumerate(text.splitlines(keepends=True), 1):
        row = cells(line) if line.lstrip().startswith("|") else []
        match = TASK_CELL.fullmatch(row[1]) if len(row) == 4 else None
        if len(row) == 4 and match is None and TASK_ID.search(row[1]):
            errors.append(
                f"line {n}: cannot read the task cell; write it as "
                f"'{PLACEHOLDER} US-xx.N title'"
            )
        if match is None:
            out.append(line)
            continue

        task, title = match["task"], match["title"].strip()
        story, owner = row[0], row[2]
        issue = issues.get(f"task:{task}")
        number = int(match["number"]) if match["number"] else None
        rows.append(Row(n, story, task, title, owner, number))

        if task not in titles:
            errors.append(f"line {n}: {task} is not a task in backlog.json")
        elif title != titles[task]:
            errors.append(f"line {n}: the title of {task} should be '{titles[task]}'")
        if story != task.rsplit(".", 1)[0]:
            errors.append(
                f"line {n}: {task} belongs to {task.rsplit('.', 1)[0]}, not {story}"
            )
        if owner not in team:
            known = ", ".join(sorted(team)) or "nobody"
            errors.append(
                f"line {n}: owner '{owner}' is not in the working agreement ({known})"
            )
        if issue is None:
            unplanned.append(task)
            out.append(line)
            continue
        if number is not None and (
            number != issue["number"] or match["url"] != issue["url"]
        ):
            errors.append(
                f"line {n}: {task} links to #{number}, but its issue is #{issue['number']}"
            )
        if number is None:
            link = f"[#{issue['number']}]({issue['url']})"
            out.append(line.replace(match["ref"], link, 1))
            filled += 1
        else:
            out.append(line)

    listed: dict[str, int] = {}
    for row in rows:
        listed[row.task] = listed.get(row.task, 0) + 1
    for task, count in sorted(listed.items()):
        if count > 1:
            errors.append(f"{task} is listed {count} times")
    stories = sorted({row.task.rsplit(".", 1)[0] for row in rows})
    for story in stories:
        missing = [
            t for t in titles if t.rsplit(".", 1)[0] == story and t not in listed
        ]
        if missing:
            errors.append(f"{story} is missing tasks: {', '.join(missing)}")

    return Result("".join(out), rows, errors, unplanned, filled)


def assign(rows: list[Row], state: dict, team: dict[str, str], repo: str) -> int:
    """Assign each task issue to its owner with the GitHub CLI. Returns failures."""
    gh = shutil.which("gh")
    if gh is None:
        print(
            "The GitHub CLI (gh) was not found. Install it from https://cli.github.com"
        )
        return len(rows)
    failures = 0
    for row in rows:
        number = state["issues"][f"task:{row.task}"]["number"]
        login = team[row.owner]
        done = subprocess.run(
            [gh, "issue", "edit", str(number), "--repo", repo, "--add-assignee", login],
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode == 0:
            print(f"  #{number:<5} {row.task:<10} assigned to {login}")
        else:
            failures += 1
            print(f"  #{number:<5} {row.task:<10} NOT assigned: {done.stderr.strip()}")
    return failures


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Fill in the task issue links in a sprint's planning notes."
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="OWNER/REPO, for example olumafecode/agentsentinel",
    )
    parser.add_argument("planning", type=Path, help="the sprint's planning.md")
    parser.add_argument(
        "--check", action="store_true", help="report only; change nothing"
    )
    parser.add_argument(
        "--assign", action="store_true", help="assign each task issue to its owner"
    )
    parser.add_argument(
        "--state", type=Path, help="board state file (default: the one for --repo)"
    )
    args = parser.parse_args(argv)

    owner, _, name = args.repo.partition("/")
    state_path = args.state or HERE / f".board-state-{owner}-{name}.json"
    if not state_path.exists():
        print(f"No board state file at {state_path}. Check --repo.")
        return 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    backlog = json.loads(BACKLOG.read_text(encoding="utf-8"))
    team = people(AGREEMENT.read_text(encoding="utf-8"))
    with args.planning.open(encoding="utf-8", newline="") as handle:
        text = handle.read()

    result = fill(text, state, backlog, team)
    if not result.rows:
        print(f"No task rows found in {args.planning}.")
        return 1
    if result.errors or result.unplanned:
        print("Nothing was changed.")
    if result.errors:
        print(f"Fix these in {args.planning} and run again:")
        for error in result.errors:
            print(f"  - {error}")
    if result.unplanned:
        which = (
            f"None of the {len(result.rows)} tasks has"
            if len(result.unplanned) == len(result.rows)
            else f"{', '.join(result.unplanned)} {'has' if len(result.unplanned) == 1 else 'have'}"
        )
        print(f"{which} an issue yet. Run plan-sprint for their sprint first.")
    if result.errors or result.unplanned:
        return 1

    print(f"{len(result.rows)} task rows checked.")
    if args.check:
        if result.filled:
            print(f"{result.filled} links still to fill in. Run again without --check.")
            return 1
        print("Every link is filled in and correct.")
        return 0
    if result.filled:
        with args.planning.open("w", encoding="utf-8", newline="") as handle:
            handle.write(result.text)
        print(f"{result.filled} links filled in.")
    else:
        print("Every link was already filled in and correct.")
    if args.assign:
        print("Assigning tasks on GitHub:")
        if assign(result.rows, state, team, args.repo):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
