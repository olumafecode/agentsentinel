#!/usr/bin/env python3
"""Build the AgentSentinel Scrum board in GitHub Projects from backlog.json.

What it creates in your GitHub account:
  * labels for item types, requirements (FR-xx, NFR-xx) and use cases (UC-xx)
  * milestones M1 to M7 with due dates
  * a public GitHub Project linked to the repository, with Status, Priority,
    Story points and Sprint (iteration) fields
  * one issue per feature, user story and sprint ceremony checklist, with
    stories as sub-issues of features
  * task sub-issues for the stories in the first sprint (later sprints get
    their tasks at their own sprint planning, with the plan-sprint command)

Requirements: Python 3.9+, the GitHub CLI (gh) signed in with the project scope:
    gh auth login
    gh auth refresh -s project

Usage:
    python setup_board.py --repo OWNER/REPO setup [--create-repo] [--invite-grader]
    python setup_board.py --repo OWNER/REPO plan-sprint "Sprint 1" [--stories US-07,US-08]
    python setup_board.py --repo OWNER/REPO status
    python setup_board.py --repo OWNER/REPO setup --dry-run      (prints the plan, changes nothing)

The script is safe to re-run. It keeps a state file next to itself
(.board-state-OWNER-REPO.json) and skips anything already created.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.parse
from datetime import date

HERE = pathlib.Path(__file__).resolve().parent
BACKLOG = HERE / "backlog.json"
GRADER = "quantic-grader"

STATUS_OPTIONS = [
    ("Backlog", "GRAY", "In the product backlog, not planned into a sprint yet"),
    ("Ready", "BLUE", "Planned into the current sprint and meets the Definition of Ready"),
    ("In progress", "YELLOW", "Someone is working on it"),
    ("In review", "PURPLE", "Pull request open or waiting for Product Owner acceptance"),
    ("Done", "GREEN", "Meets the Definition of Done"),
]
PRIORITY_OPTIONS = [
    ("Must", "RED", "Must have for this release"),
    ("Should", "ORANGE", "Should have; first to drop if time runs short"),
    ("Could", "YELLOW", "Could have if capacity allows"),
    ("Won't", "GRAY", "Won't have in this release; kept to record the scope decision"),
]
# Used only if GitHub refuses to rename the built-in Status options.
STATUS_FALLBACK = {"Backlog": "Todo", "Ready": "Todo", "In progress": "In Progress", "In review": "In Progress", "Done": "Done"}

TYPE_LABELS = {
    "type:feature": ("5319e7", "Feature (epic): groups related user stories"),
    "type:story": ("1d76db", "User story: delivers value and has acceptance criteria"),
    "type:task": ("c5def5", "Task: a constituent piece of work inside a user story"),
    "type:bug": ("d73a4a", "Defect found in testing or review"),
    "type:ceremony": ("fbca04", "Sprint events: planning, weekly scrum, review with demo, retrospective"),
}
FR_COLOR, NFR_COLOR, UC_COLOR = "0e8a16", "d93f0b", "006b75"


# ---------------------------------------------------------------- helpers
def say(msg=""):
    print(msg, flush=True)


def fmt_day(iso):
    d = date.fromisoformat(iso)
    return f"{d:%a} {d.day} {d:%b} {d.year}"


def fmt_range(start, end):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    return f"{a.day} {a:%b} to {b.day} {b:%b} {b.year}"


def short(text, n=100):
    return text if len(text) <= n else text[: n - 3].rstrip() + "..."


class GHError(RuntimeError):
    pass


class GH:
    """Thin wrapper around the gh CLI with retry on GitHub rate limits."""

    RATE_HINTS = ("secondary rate limit", "submitted too quickly", "abuse detection", "api rate limit exceeded")
    TRANSIENT_HINTS = ("http 502", "http 503", "http 504", "something went wrong", "timeout", "connection reset")

    def __init__(self, pause):
        self.exe = shutil.which("gh")
        self.pause = pause

    def _run(self, args, body=None):
        proc = subprocess.run([self.exe] + args, input=body, capture_output=True, text=True, encoding="utf-8", check=False)
        return proc.returncode, proc.stdout, proc.stderr

    def _retrying(self, args, body):
        for attempt in range(1, 7):
            code, out, err = self._run(args, body)
            text = (out + " " + err).lower()
            if code == 0:
                return code, out, err
            if any(h in text for h in self.RATE_HINTS):
                wait = 60 * attempt
                say(f"    GitHub rate limit reached; waiting {wait} s before retrying (attempt {attempt} of 6)")
                time.sleep(wait)
                continue
            if any(h in text for h in self.TRANSIENT_HINTS) and attempt < 4:
                time.sleep(10 * attempt)
                continue
            return code, out, err
        return code, out, err

    def graphql(self, query, variables=None, mutation=False):
        body = json.dumps({"query": query, "variables": variables or {}})
        code, out, err = self._retrying(["api", "graphql", "--input", "-"], body)
        try:
            payload = json.loads(out) if out.strip() else {}
        except json.JSONDecodeError:
            payload = {}
        if payload.get("errors") or code != 0:
            msgs = "; ".join(e.get("message", str(e)) for e in payload.get("errors", [])) or err.strip() or out.strip()
            raise GHError(msgs)
        if mutation and self.pause:
            time.sleep(self.pause)
        return payload["data"]

    def rest(self, method, path, body=None):
        args = ["api", "--method", method, path]
        if body is not None:
            args += ["--input", "-"]
        code, out, err = self._retrying(args, json.dumps(body) if body is not None else None)
        try:
            payload = json.loads(out) if out.strip() else None
        except json.JSONDecodeError:
            payload = None
        if method != "GET" and self.pause:
            time.sleep(self.pause)
        return code, payload, err


# ---------------------------------------------------------------- GraphQL documents
Q_REPO = """
query RepoInfo($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
    url
    nameWithOwner
    owner { id login __typename }
  }
}"""

M_CREATE_PROJECT = """
mutation CreateProject($ownerId: ID!, $title: String!, $repositoryId: ID) {
  createProjectV2(input: {ownerId: $ownerId, title: $title, repositoryId: $repositoryId}) {
    projectV2 { id number url }
  }
}"""

M_UPDATE_PROJECT = """
mutation UpdateProject($projectId: ID!, $public: Boolean, $shortDescription: String, $readme: String) {
  updateProjectV2(input: {projectId: $projectId, public: $public, shortDescription: $shortDescription, readme: $readme}) {
    projectV2 { id public }
  }
}"""

Q_FIELDS = """
query ProjectFields($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      url
      fields(first: 50) {
        nodes {
          __typename
          ... on ProjectV2Field { id name dataType }
          ... on ProjectV2SingleSelectField { id name dataType options { id name } }
          ... on ProjectV2IterationField {
            id
            name
            dataType
            configuration {
              iterations { id title startDate duration }
              completedIterations { id title startDate duration }
            }
          }
        }
      }
    }
  }
}"""

M_UPDATE_FIELD = """
mutation UpdateField($fieldId: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {
  updateProjectV2Field(input: {fieldId: $fieldId, singleSelectOptions: $options}) {
    projectV2Field { __typename }
  }
}"""

M_CREATE_FIELD = """
mutation CreateField($projectId: ID!, $name: String!, $dataType: ProjectV2CustomFieldType!,
                     $options: [ProjectV2SingleSelectFieldOptionInput!],
                     $iterations: ProjectV2IterationFieldConfigurationInput) {
  createProjectV2Field(input: {projectId: $projectId, name: $name, dataType: $dataType,
                               singleSelectOptions: $options, iterationConfiguration: $iterations}) {
    projectV2Field { __typename }
  }
}"""

M_CREATE_ISSUE = """
mutation CreateIssue($repositoryId: ID!, $title: String!, $body: String, $labelIds: [ID!], $milestoneId: ID, $parentIssueId: ID) {
  createIssue(input: {repositoryId: $repositoryId, title: $title, body: $body, labelIds: $labelIds,
                      milestoneId: $milestoneId, parentIssueId: $parentIssueId}) {
    issue { id number url }
  }
}"""

M_ADD_ITEM = """
mutation AddItem($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item { id }
  }
}"""

Q_ISSUE_ITEMS = """
query IssueItems($issueId: ID!) {
  node(id: $issueId) {
    ... on Issue {
      projectItems(first: 50) {
        nodes { id project { id } }
      }
    }
  }
}"""


def set_fields_document(n):
    """One request that sets n field values on one project item (aliased mutations)."""
    params = ["$projectId: ID!", "$itemId: ID!"]
    parts = []
    for i in range(n):
        params += [f"$f{i}: ID!", f"$v{i}: ProjectV2FieldValue!"]
        parts.append(
            f"  s{i}: updateProjectV2ItemFieldValue(input: {{projectId: $projectId, itemId: $itemId, fieldId: $f{i}, value: $v{i}}}) {{ projectV2Item {{ id }} }}"
        )
    return "mutation SetFields(" + ", ".join(params) + ") {\n" + "\n".join(parts) + "\n}"


# ---------------------------------------------------------------- issue bodies
def req_lines(s, data):
    reqs = data["requirements"]
    lines = []
    for code in s["fr"]:
        lines.append(f"- **{code}** {reqs['fr'][code]}")
    for code in s["nfr"]:
        q = reqs["nfr"][code]
        lines.append(f"- **{code} {q['quality']}** {q['text']}")
    for code in s["tests"]:
        lines.append(f"- **{code}** {reqs['acceptance_tests'][code]}")
    return lines


def story_body(s, data, repo_url):
    sprints = {x["title"]: x for x in data["sprints"]}
    feats = {f["id"]: f for f in data["features"]}
    ucs = data["requirements"]["use_cases"]
    if s["priority"] == "Won't":
        return (f"**Priority:** Won't have (this release)\n\n**Why:** {s['source']}\n\n"
                "Kept on the board so the scope decision is visible. Do not plan this item into a sprint.")
    sp = sprints.get(s["sprint"])
    sprint_txt = f"{sp['title']} ({fmt_range(sp['start'], sp['end'])})" if sp else "Not scheduled (pulled in at sprint planning if capacity allows)"
    uc_txt = ", ".join(f"{u} {ucs[u]}" for u in s["uc"]) or "None (enabler)"
    out = [
        f"**Feature:** {s['feature']} {feats[s['feature']]['title']}" if s["feature"] else "",
        f"**Source:** {s['source']}",
        "",
        "### User story",
        f"As {s['as_a']}, I want {s['i_want']}, so that {s['so_that']}.",
        "",
        "### Acceptance criteria",
        *[f"- [ ] {a}" for a in s["acceptance"]],
        "",
        "### Traceability",
        "| Use cases | Functional requirements | Non-functional requirements | Acceptance tests |",
        "|---|---|---|---|",
        f"| {uc_txt} | {', '.join(s['fr']) or 'None'} | {', '.join(s['nfr']) or 'None'} | {', '.join(s['tests']) or 'None'} |",
    ]
    rl = req_lines(s, data)
    if rl:
        out += ["", "<details><summary>Requirement and test wording</summary>", "", *rl, "", "</details>"]
    out += [
        "",
        "### Planning",
        f"Priority: **{s['priority']}** | Story points: **{s['points']}** | Sprint: **{sprint_txt}** | Milestone: **{s['milestone'] or 'None'}**",
        "",
        "### Suggested tasks",
        "Confirmed, split or changed at sprint planning, then created as sub-issues and assigned.",
        *[f"{i}. {t['title']} ({t['role']})" for i, t in enumerate(s["tasks"], 1)],
        "",
        "### Done means",
        (f"Every acceptance criterion above is checked and the [Definition of Done]({repo_url}/blob/main/docs/agile/definition-of-ready-and-done.md) is met. "
         "The Product Owner closes this story after accepting it; pull requests close tasks, not stories."),
    ]
    return "\n".join(x for x in out if x is not None)


def task_body(t, s, repo_url):
    return "\n".join([
        f"Part of **{s['id']} {s['title']}**.",
        "",
        f"Suggested owner: {t['role']} (assign the person at sprint planning).",
        "",
        "Done when:",
        "- [ ] The change is merged through a reviewed pull request with green CI",
        "- [ ] Tests for this change are added or updated",
        "- [ ] The pull request description says `Closes #<this task number>` so this task closes on merge",
        "",
        f"Story acceptance criteria and traceability are on the parent story. Board guide: {repo_url}/blob/main/docs/agile/board-guide.md",
    ])


def feature_body(f, stories):
    rows = [f"- {s['id']} {s['title']} ({s['priority']}, {s['sprint'] or 'not scheduled'})" for s in stories]
    return "\n".join([
        f"**Feature {f['id']}:** {f['description']}",
        "",
        "User stories in this feature (tracked as sub-issues, so the progress bar shows completion):",
        *rows,
    ])


def ceremony_body(sp, repo_url):
    folder = sp["title"].lower().replace(" ", "-")
    notes = f"{repo_url}/tree/main/docs/agile/sprints/{folder}"
    lines = [
        f"**{sp['title']}: {sp['name']}** ({fmt_range(sp['start'], sp['end'])})",
        "",
        f"**Sprint goal:** {sp['goal']}",
    ]
    if sp.get("note"):
        lines += ["", f"Note: {sp['note']}"]
    lines += ["", "Tick each event when it has happened and its notes are saved in " + notes, ""]
    events = []
    if sp.get("planning"):
        events.append((sp["planning"], 0, f"- [ ] Sprint planning ({fmt_day(sp['planning'])}): sprint backlog chosen, tasks created and assigned"))
    for d in sp.get("scrums", []):
        events.append((d, 1, f"- [ ] Weekly scrum ({fmt_day(d)})"))
    if sp.get("refinement"):
        events.append((sp["refinement"], 1, f"- [ ] Backlog refinement ({fmt_day(sp['refinement'])}): next sprint's stories meet the Definition of Ready"))
    lines += [e[2] for e in sorted(events)]
    if sp.get("review"):
        lines.append(f"- [ ] Sprint review with a recorded demo of working software for the Product Owner ({fmt_day(sp['review'])}). Video link: ")
        lines.append(f"- [ ] Retrospective ({fmt_day(sp['review'])}): one or two improvements recorded")
        lines.append("- [ ] Velocity recorded (story points of stories accepted as Done)")
    return "\n".join(lines)


def project_readme(data, repo_url):
    sp_rows = [f"| {s['title']} | {fmt_range(s['start'], s['end'])} | {s['goal']} |" for s in data["sprints"]]
    return "\n".join([
        "# AgentSentinel Scrum Board",
        "",
        "Product backlog, sprint backlogs, user stories and their tasks for the AgentSentinel MSSE capstone.",
        "",
        "## How this board is organized",
        "- **Features** (label `type:feature`) group user stories. Stories are sub-issues of features.",
        "- **User stories** (label `type:story`) carry acceptance criteria, story points, priority (MoSCoW) and labels for the functional requirements (FR-xx), non-functional requirements (NFR-xx) and use cases (UC-xx) they deliver.",
        "- **Tasks** (label `type:task`) are sub-issues of stories, created and assigned at each sprint planning.",
        "- **Ceremonies** (label `type:ceremony`) hold the checklist of planning, weekly scrums, review with recorded demo and retrospective for each sprint.",
        "",
        "Status: Backlog, Ready, In progress, In review, Done. Filter by a requirement label (for example `label:FR-05`) to see every story that delivers it.",
        "",
        "## Sprints",
        "| Sprint | Dates | Goal |",
        "|---|---|---|",
        *sp_rows,
        "",
        f"Submission target: {fmt_day(data['project']['submission_due'])}. Final cut-off: {fmt_day(data['project']['final_cutoff'])}.",
        "",
        "## Documents",
        f"- Product backlog and traceability: {repo_url}/blob/main/docs/agile/product-backlog.md",
        f"- Board guide: {repo_url}/blob/main/docs/agile/board-guide.md",
        f"- Definition of Ready and Done: {repo_url}/blob/main/docs/agile/definition-of-ready-and-done.md",
        f"- Sprint calendar: {repo_url}/blob/main/docs/agile/sprint-calendar.md",
    ])


# ---------------------------------------------------------------- the board
class Board:
    def __init__(self, args):
        self.args = args
        self.owner, self.name = args.repo.split("/", 1)
        self.data = json.loads(BACKLOG.read_text(encoding="utf-8"))
        self.state_path = HERE / f".board-state-{self.owner}-{self.name}.json"
        self.state = json.loads(self.state_path.read_text(encoding="utf-8")) if self.state_path.exists() else {}
        self.state.setdefault("labels", {})
        self.state.setdefault("milestones", {})
        self.state.setdefault("issues", {})
        self.gh = GH(args.pause)
        self.stories = {s["id"]: s for s in self.data["stories"]}
        self.sprints = {s["title"]: s for s in self.data["sprints"]}

    def save(self):
        self.state_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    # ---- preflight and repository
    def preflight(self):
        if not self.gh.exe:
            sys.exit("The GitHub CLI (gh) was not found. Install it from https://cli.github.com and run: gh auth login")
        code, out, err = self.gh._run(["auth", "status"])
        if code != 0:
            sys.exit("gh is not signed in. Run: gh auth login   then: gh auth refresh -s project")
        text = out + err
        if "Token scopes" in text and "'project'" not in text and not os.environ.get("GH_TOKEN"):
            sys.exit("Your gh token lacks the 'project' scope. Run: gh auth refresh -s project   and then re-run this script.")

    def repo(self):
        try:
            r = self.gh.graphql(Q_REPO, {"owner": self.owner, "name": self.name})["repository"]
        except GHError as e:
            if "Could not resolve to a Repository" not in str(e):
                raise
            r = None
        if r is None:
            if not self.args.create_repo:
                sys.exit(f"Repository {self.args.repo} was not found. Create it first, or re-run with --create-repo.")
            say(f"Creating private repository {self.args.repo}")
            code, out, err = self.gh._run(["repo", "create", self.args.repo, "--private",
                                           "--description", "AgentSentinel: runtime governance for AI agents in banking (MSSE capstone)"])
            if code != 0:
                sys.exit(f"Could not create the repository: {err.strip() or out.strip()}")
            r = self.gh.graphql(Q_REPO, {"owner": self.owner, "name": self.name})["repository"]
        self.state["repo"] = {"id": r["id"], "url": r["url"], "owner_id": r["owner"]["id"], "owner_type": r["owner"]["__typename"]}
        self.save()
        return r

    def invite_grader(self):
        code, _payload, err = self.gh.rest("PUT", f"repos/{self.owner}/{self.name}/collaborators/{GRADER}", {"permission": "pull"})
        if code == 0:
            say(f"  {GRADER} invited (or already a collaborator)")
        else:
            say(f"  Could not invite {GRADER}: {err.strip()}. Add the account under Settings > Collaborators.")

    # ---- labels and milestones
    def labels(self):
        wanted = dict(TYPE_LABELS)
        reqs = self.data["requirements"]
        for code, text in reqs["fr"].items():
            wanted[code] = (FR_COLOR, short(text))
        for code, q in reqs["nfr"].items():
            wanted[code] = (NFR_COLOR, short(f"{q['quality']}: {q['text']}"))
        for code, text in reqs["use_cases"].items():
            wanted[code] = (UC_COLOR, short(text))
        existing, page = {}, 1
        while True:
            code, payload, err = self.gh.rest("GET", f"repos/{self.owner}/{self.name}/labels?per_page=100&page={page}")
            if code != 0:
                raise GHError(f"Could not list labels: {err.strip()}")
            for lab in payload or []:
                existing[lab["name"]] = lab["node_id"]
            if not payload or len(payload) < 100:
                break
            page += 1
        made = 0
        for name, (color, desc) in wanted.items():
            if name in existing:
                self.state["labels"][name] = existing[name]
                continue
            code, payload, err = self.gh.rest("POST", f"repos/{self.owner}/{self.name}/labels",
                                              {"name": name, "color": color, "description": desc})
            if code != 0:
                code, payload, _err = self.gh.rest("GET", f"repos/{self.owner}/{self.name}/labels/{urllib.parse.quote(name, safe='')}")
                if code != 0:
                    raise GHError(f"Could not create label {name}: {err.strip()}")
            else:
                made += 1
            self.state["labels"][name] = payload["node_id"]
        self.save()
        say(f"  labels ready ({made} created, {len(wanted) - made} already there)")

    def milestones(self):
        code, payload, err = self.gh.rest("GET", f"repos/{self.owner}/{self.name}/milestones?state=all&per_page=100")
        if code != 0:
            raise GHError(f"Could not list milestones: {err.strip()}")
        existing = {m["title"]: m["node_id"] for m in payload or []}
        for m in self.data["milestones"]:
            if m["title"] in existing:
                self.state["milestones"][m["id"]] = existing[m["title"]]
                continue
            code, payload, err = self.gh.rest("POST", f"repos/{self.owner}/{self.name}/milestones",
                                              {"title": m["title"], "description": m["description"], "due_on": f"{m['due']}T12:00:00Z"})
            if code != 0:
                raise GHError(f"Could not create milestone {m['title']}: {err.strip()}")
            self.state["milestones"][m["id"]] = payload["node_id"]
        self.save()
        say("  milestones M1 to M7 ready")

    # ---- project and fields
    def project(self):
        if "project" not in self.state:
            p = self.gh.graphql(M_CREATE_PROJECT, {"ownerId": self.state["repo"]["owner_id"],
                                                   "title": self.data["project"]["title"],
                                                   "repositoryId": self.state["repo"]["id"]}, mutation=True)["createProjectV2"]["projectV2"]
            self.state["project"] = p
            self.save()
            say(f"  project created: {p['url']}")
        p = self.state["project"]
        if not self.state.get("project_configured"):
            try:
                self.gh.graphql(M_UPDATE_PROJECT, {"projectId": p["id"], "public": not self.args.private,
                                                   "shortDescription": self.data["project"]["short_description"],
                                                   "readme": project_readme(self.data, self.state["repo"]["url"])}, mutation=True)
                self.state["project_configured"] = True
                self.save()
                say("  project visibility set to " + ("private" if self.args.private else "public") + ", description and README added")
            except GHError as e:
                say(f"  WARNING: could not update project settings ({e}). Set visibility to Public in the project's Settings.")

    def read_fields(self):
        nodes = self.gh.graphql(Q_FIELDS, {"projectId": self.state["project"]["id"]})["node"]["fields"]["nodes"]
        return {n["name"]: n for n in nodes if n.get("name")}

    def fields(self):
        pid = self.state["project"]["id"]
        f = self.read_fields()
        # Status: rename the built-in options to the Scrum flow.
        status = f.get("Status")
        names = [o["name"] for o in status.get("options", [])] if status else []
        if status and names != [o[0] for o in STATUS_OPTIONS]:
            try:
                self.gh.graphql(M_UPDATE_FIELD, {"fieldId": status["id"], "options": [
                    {"name": n, "color": c, "description": d} for n, c, d in STATUS_OPTIONS]}, mutation=True)
                say("  Status options set: " + ", ".join(o[0] for o in STATUS_OPTIONS))
            except GHError as e:
                say(f"  WARNING: could not change Status options ({e}). Using GitHub's default options instead;"
                    " rename them by hand in the project settings if you want the five-step flow.")
        if "Priority" not in f:
            self.gh.graphql(M_CREATE_FIELD, {"projectId": pid, "name": "Priority", "dataType": "SINGLE_SELECT", "options": [
                {"name": n, "color": c, "description": d} for n, c, d in PRIORITY_OPTIONS]}, mutation=True)
            say("  Priority field created (Must, Should, Could, Won't)")
        if "Story points" not in f:
            self.gh.graphql(M_CREATE_FIELD, {"projectId": pid, "name": "Story points", "dataType": "NUMBER"}, mutation=True)
            say("  Story points field created")
        if "Sprint" not in f:
            sp = self.data["sprints"]
            try:
                self.gh.graphql(M_CREATE_FIELD, {"projectId": pid, "name": "Sprint", "dataType": "ITERATION", "iterations": {
                    "startDate": sp[0]["start"], "duration": 14,
                    "iterations": [{"title": s["title"], "startDate": s["start"], "duration": s["days"]} for s in sp]}}, mutation=True)
                say("  Sprint field created with " + ", ".join(s["title"] for s in sp))
            except GHError as e:
                say(f"  WARNING: could not create the Sprint iteration field ({e}).")
                say("  Create it by hand: project Settings > New field > Iteration, name it 'Sprint', and add the iterations")
                say("  listed in docs/agile/sprint-calendar.md with the same titles. Then re-run this script to fill in sprints.")
        f = self.read_fields()
        ids = {"status": None, "priority": None, "points": None, "sprint": None}
        if "Status" in f:
            opts = {o["name"]: o["id"] for o in f["Status"]["options"]}
            ids["status"] = {"id": f["Status"]["id"], "options": {
                k: opts.get(k) or opts.get(STATUS_FALLBACK[k]) for k, _, _ in STATUS_OPTIONS}}
        if "Priority" in f:
            ids["priority"] = {"id": f["Priority"]["id"], "options": {o["name"]: o["id"] for o in f["Priority"]["options"]}}
        if "Story points" in f:
            ids["points"] = {"id": f["Story points"]["id"]}
        if "Sprint" in f:
            conf = f["Sprint"]["configuration"]
            its = conf["iterations"] + conf["completedIterations"]
            ids["sprint"] = {"id": f["Sprint"]["id"], "iterations": {i["title"]: i["id"] for i in its}}
        self.state["fields"] = ids
        self.save()

    # ---- issues and project items
    def issue(self, key, title, body, labels, milestone=None, parent=None):
        rec = self.state["issues"].get(key)
        if rec is None:
            variables = {
                "repositoryId": self.state["repo"]["id"], "title": title, "body": body,
                "labelIds": [self.state["labels"][x] for x in labels],
                "milestoneId": self.state["milestones"].get(milestone) if milestone else None,
                "parentIssueId": self.state["issues"][parent]["id"] if parent else None,
            }
            try:
                iss = self.gh.graphql(M_CREATE_ISSUE, variables, mutation=True)["createIssue"]["issue"]
            except GHError as e:
                if not parent:
                    raise
                say(f"    note: creating {key} as a sub-issue failed ({e}); creating it unlinked. Link it to {parent} by hand.")
                variables["parentIssueId"] = None
                iss = self.gh.graphql(M_CREATE_ISSUE, variables, mutation=True)["createIssue"]["issue"]
            rec = {"id": iss["id"], "number": iss["number"], "url": iss["url"], "set": {}}
            self.state["issues"][key] = rec
            self.save()
            say(f"    #{iss['number']:<4} {title}")
        if "item" not in rec:
            try:
                item = self.gh.graphql(M_ADD_ITEM, {"projectId": self.state["project"]["id"], "contentId": rec["id"]}, mutation=True)
                rec["item"] = item["addProjectV2ItemById"]["item"]["id"]
            except GHError as e:
                # GitHub can add a sub-issue to the board by itself when its parent is already
                # on the board. In that case, look up the item GitHub created and use it.
                if "already exists" not in str(e).lower():
                    raise
                rec["item"] = self.existing_item(rec["id"])
            self.save()
        return rec

    def existing_item(self, issue_id):
        pid = self.state["project"]["id"]
        for attempt in range(5):
            node = self.gh.graphql(Q_ISSUE_ITEMS, {"issueId": issue_id})["node"] or {}
            for it in node.get("projectItems", {}).get("nodes", []):
                if it["project"]["id"] == pid:
                    return it["id"]
            time.sleep(2 * (attempt + 1))
        raise GHError("GitHub says the issue is already on the board but did not return its item. Wait a minute and re-run.")

    def set_fields(self, key, status=None, priority=None, points=None, sprint=None, force=False):
        rec, fl = self.state["issues"][key], self.state["fields"]
        wanted = []
        if status and fl["status"] and fl["status"]["options"].get(status):
            wanted.append(("status", status, fl["status"]["id"], {"singleSelectOptionId": fl["status"]["options"][status]}))
        if priority and fl["priority"] and fl["priority"]["options"].get(priority):
            wanted.append(("priority", priority, fl["priority"]["id"], {"singleSelectOptionId": fl["priority"]["options"][priority]}))
        if points is not None and points > 0 and fl["points"]:
            wanted.append(("points", points, fl["points"]["id"], {"number": float(points)}))
        if sprint and fl["sprint"] and fl["sprint"]["iterations"].get(sprint):
            wanted.append(("sprint", sprint, fl["sprint"]["id"], {"iterationId": fl["sprint"]["iterations"][sprint]}))
        todo = [w for w in wanted if force or rec["set"].get(w[0]) != w[1]]
        if not todo:
            return
        variables = {"projectId": self.state["project"]["id"], "itemId": rec["item"]}
        for i, (_, _, fid, val) in enumerate(todo):
            variables[f"f{i}"], variables[f"v{i}"] = fid, val
        self.gh.graphql(set_fields_document(len(todo)), variables, mutation=True)
        for name, value, _, _ in todo:
            rec["set"][name] = value
        self.save()

    def story_issue(self, s, status):
        labels = ["type:story"] + s["fr"] + s["nfr"] + s["uc"]
        parent = f"feature:{s['feature']}" if s["feature"] else None
        self.issue(f"story:{s['id']}", f"{s['id']} {s['title']}", story_body(s, self.data, self.state["repo"]["url"]),
                   labels, s["milestone"], parent)
        self.set_fields(f"story:{s['id']}", status=status, priority=s["priority"], points=s["points"], sprint=s["sprint"])

    def task_issues(self, s, sprint, status="Ready"):
        for i, t in enumerate(s["tasks"], 1):
            key = f"task:{s['id']}.{i}"
            self.issue(key, f"{s['id']}.{i} {t['title']}", task_body(t, s, self.state["repo"]["url"]),
                       ["type:task"], s["milestone"], f"story:{s['id']}")
            self.set_fields(key, status=status, sprint=sprint)

    # ---- commands
    def setup(self):
        first = self.args.task_sprint
        say("1. Checking the repository")
        self.repo()
        if self.args.invite_grader:
            self.invite_grader()
        say("2. Labels and milestones")
        self.labels()
        self.milestones()
        say("3. Project and fields")
        self.project()
        self.fields()
        say("4. Features")
        for f in self.data["features"]:
            members = [s for s in self.data["stories"] if s["feature"] == f["id"]]
            self.issue(f"feature:{f['id']}", f"{f['id']} {f['title']}", feature_body(f, members), ["type:feature"])
            self.set_fields(f"feature:{f['id']}", status="Backlog")
        say("5. Sprint ceremony checklists")
        for sp in self.data["sprints"]:
            if not sp.get("planning"):
                continue
            key = f"ceremony:{sp['title']}"
            self.issue(key, f"{sp['title']} ceremonies: {sp['name']} ({fmt_range(sp['start'], sp['end'])})",
                       ceremony_body(sp, self.state["repo"]["url"]), ["type:ceremony"])
            self.set_fields(key, status="Ready" if sp["title"] == first else "Backlog", sprint=sp["title"])
        say("6. User stories (product backlog)")
        for s in self.data["stories"]:
            self.story_issue(s, "Ready" if s["sprint"] == first else "Backlog")
        say(f"7. Tasks for {first}")
        for s in self.data["stories"]:
            if s["sprint"] == first:
                self.task_issues(s, first)
        self.summary()

    def plan_sprint(self):
        if "fields" not in self.state:
            sys.exit("Run the setup command first.")
        sprint = self.args.sprint
        if sprint not in self.sprints:
            sys.exit(f"Unknown sprint '{sprint}'. Use one of: " + ", ".join(self.sprints))
        picked = [s.strip() for s in self.args.stories.split(",")] if self.args.stories else \
            [s["id"] for s in self.data["stories"] if s["sprint"] == sprint]
        unknown = [p for p in picked if p not in self.stories]
        if unknown:
            sys.exit("Unknown story IDs: " + ", ".join(unknown))
        say(f"Planning {sprint}: " + ", ".join(picked))
        for sid in picked:
            s = dict(self.stories[sid], sprint=sprint)
            self.story_issue(s, "Ready")
            self.set_fields(f"story:{sid}", status="Ready", sprint=sprint)
            self.task_issues(s, sprint)
        key = f"ceremony:{sprint}"
        if key in self.state["issues"]:
            self.set_fields(key, status="In progress")
        pts = sum(self.stories[p]["points"] for p in picked)
        say(f"\n{sprint} planned: {len(picked)} {'story' if len(picked) == 1 else 'stories'}, {pts} story points. Assign each task to a person on the board.")
        say(f"Board: {self.state['project']['url']}")

    def status(self):
        if "project" not in self.state:
            sys.exit("No board yet. Run the setup command first.")
        names = {"feature": "features", "ceremony": "ceremony checklists", "story": "stories", "task": "tasks"}
        kinds = {}
        for k in self.state["issues"]:
            kinds[k.split(":")[0]] = kinds.get(k.split(":")[0], 0) + 1
        say(f"Board: {self.state['project']['url']}")
        say("Issues created: " + ", ".join(f"{v} {names.get(k, k)}" for k, v in sorted(kinds.items())))

    def summary(self):
        url = self.state["project"]["url"]
        say("")
        say("Done. Board: " + url)
        say("")
        say("Finish these steps in the browser (GitHub has no API for them yet):")
        say("  a. Create the views in docs/agile/board-guide.md (Product backlog, Sprint board, Sprint backlog, Roadmap, Traceability, My tasks)")
        say("  b. Turn on the workflows listed in the board guide (Workflows menu)")
        say("  c. Put the board link in README.md under 'Scrum board'")
        if self.state["repo"].get("owner_type") == "User":
            say("  d. If the repository is private, only people with access to it (such as quantic-grader) can see its items on the board")


# ---------------------------------------------------------------- dry run
def dry_run(args):
    data = json.loads(BACKLOG.read_text(encoding="utf-8"))
    first = args.task_sprint
    stories = data["stories"]
    tasks = [t for s in stories if s["sprint"] == first for t in s["tasks"]]
    ceremonies = [s for s in data["sprints"] if s.get("planning")]
    reqs = data["requirements"]
    say(f"Dry run for {args.repo}. Nothing will be changed.")
    say(f"  labels: {len(TYPE_LABELS) + len(reqs['fr']) + len(reqs['nfr']) + len(reqs['use_cases'])}")
    say(f"  milestones: {', '.join(m['id'] for m in data['milestones'])}")
    say(f"  project: '{data['project']['title']}' ({'private' if args.private else 'public'}) with Status, Priority, Story points, Sprint")
    say("  sprints: " + ", ".join(f"{s['title']} {s['start']} ({s['days']}d)" for s in data["sprints"]))
    say(f"  issues: {len(data['features'])} features, {len(ceremonies)} ceremony checklists, {len(stories)} stories, {len(tasks)} tasks for {first}")
    for s in stories:
        say(f"    {s['id']:7} {s['priority']:6} {s['points']:>2} pts  {s['sprint'] or '-':11} {s['title']}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Create and maintain the AgentSentinel Scrum board in GitHub Projects.")
    p.add_argument("--repo", required=True, help="OWNER/REPO, for example olumafecode/agentsentinel")
    p.add_argument("--pause", type=float, default=1.0, help="seconds to wait after each change (keeps clear of GitHub rate limits)")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("setup", help="create labels, milestones, project, fields, features, stories and first-sprint tasks")
    s.add_argument("--create-repo", action="store_true", help="create the repository (private) if it does not exist")
    s.add_argument("--invite-grader", action="store_true", help=f"invite {GRADER} to the repository with read access")
    s.add_argument("--private", action="store_true", help="keep the project private (default is public so the board link works for reviewers)")
    s.add_argument("--task-sprint", default="Sprint 0", help="sprint whose tasks are created now (default: Sprint 0)")
    s.add_argument("--dry-run", action="store_true", help="print what would be created and stop")
    ps = sub.add_parser("plan-sprint", help="at sprint planning: mark the sprint's stories Ready and create their task sub-issues")
    ps.add_argument("sprint", help='sprint title, for example "Sprint 1"')
    ps.add_argument("--stories", help="comma-separated story IDs to plan instead of the ones scheduled in backlog.json")
    sub.add_parser("status", help="show the board link and what has been created")
    args = p.parse_args()
    if "/" not in args.repo:
        sys.exit("--repo must look like OWNER/REPO")
    if args.command == "setup" and args.dry_run:
        return dry_run(args)
    board = Board(args)
    board.preflight()
    try:
        {"setup": board.setup, "plan-sprint": board.plan_sprint, "status": board.status}[args.command]()
    except GHError as e:
        sys.exit(f"\nGitHub returned an error: {e}\nNothing already created is lost; fix the cause and re-run the same command.")


if __name__ == "__main__":
    main()
