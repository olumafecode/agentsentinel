#!/usr/bin/env python3
"""Regenerate docs/agile/product-backlog.md and docs/agile/sprint-calendar.md from tools/board/backlog.json.

Run from anywhere: python tools/board/build_docs.py
"""
import json
import pathlib
from datetime import date

KIT = pathlib.Path(__file__).resolve().parents[2]  # repository root
D = json.loads((KIT / "tools/board/backlog.json").read_text(encoding="utf-8"))
REQ = D["requirements"]
STORIES = D["stories"]
SPRINTS = D["sprints"]
FEATS = {f["id"]: f for f in D["features"]}
MS = {m["id"]: m for m in D["milestones"]}


def day(iso):
    d = date.fromisoformat(iso)
    return f"{d:%a} {d.day} {d:%b} {d.year}"


def rng(a, b):
    a, b = date.fromisoformat(a), date.fromisoformat(b)
    return f"{a.day} {a:%b} to {b.day} {b:%b} {b.year}"


def ids(xs):
    return ", ".join(xs) if xs else "None"


def story_order(s):
    order = [x["title"] for x in SPRINTS]
    pri = ["Must", "Should", "Could", "Won't"]
    return (order.index(s["sprint"]) if s["sprint"] in order else 99, pri.index(s["priority"]))


scheduled = sorted([s for s in STORIES if s["sprint"]], key=story_order)
unscheduled = [s for s in STORIES if not s["sprint"] and s["priority"] != "Won't"]
wont = [s for s in STORIES if s["priority"] == "Won't"]

# ------------------------------------------------------------------ product backlog
L = []
w = L.append
w("# AgentSentinel product backlog")
w("")
w("This file is the baseline product backlog and traceability record. It is generated from `tools/board/backlog.json`, "
  "the same file the board setup script reads. Once the board exists, the board is the working copy: stories move, "
  "split and get re-estimated there. Regenerate this file at the end of each sprint if the plan changes.")
w("")
w("IDs match the approved proposal: use cases UC-01 to UC-12, functional requirements FR-01 to FR-20, non-functional "
  "requirements NFR-01 to NFR-14, acceptance tests AT-01 to AT-15 and user stories US-01 to US-11. Proposal stories "
  "that were too large for one sprint are split with a letter (US-02a and US-02b). Stories US-12 onward were added "
  "so that every piece of delivery work, including setup, data and evaluation, is on the board.")
w("")
w("## Backlog at a glance")
w("")
w("| Sprint | Dates | Sprint goal | Stories | Points |")
w("|---|---|---|---|---|")
for sp in SPRINTS:
    ss = [s for s in STORIES if s["sprint"] == sp["title"]]
    w(f"| {sp['title']}: {sp['name']} | {rng(sp['start'], sp['end'])} | {sp['goal']} | {ids([s['id'] for s in ss]) if ss else 'None'} | {sum(s['points'] for s in ss)} |")
w(f"| Not scheduled | | Pulled in at sprint planning only if capacity allows | {ids([s['id'] for s in unscheduled])} | {sum(s['points'] for s in unscheduled)} |")
w("")
must_pts = sum(s["points"] for s in STORIES if s["priority"] == "Must")
w(f"Must-have work totals {must_pts} story points across {sum(1 for s in STORIES if s['priority'] == 'Must')} stories. "
  "Should and Could items are the first to drop if velocity is lower than planned; Won't items are listed so the scope decision is visible.")
w("")
w("## Features")
w("")
w("| Feature | Description | Stories |")
w("|---|---|---|")
for f in D["features"]:
    w(f"| {f['id']} {f['title']} | {f['description']} | {ids([s['id'] for s in STORIES if s['feature'] == f['id']])} |")
w("")
w("## User stories")
w("")
w("| ID | Story | Feature | Priority | Points | Sprint | Milestone | Use cases | FR | NFR | Tests |")
w("|---|---|---|---|---|---|---|---|---|---|---|")
for s in scheduled + unscheduled + wont:
    w(f"| {s['id']} | {s['title']} | {s['feature'] or ''} | {s['priority']} | {s['points'] or ''} | {s['sprint'] or ''} | {s['milestone'] or ''} | "
      f"{', '.join(s['uc'])} | {', '.join(s['fr'])} | {', '.join(s['nfr'])} | {', '.join(s['tests'])} |")
w("")
w("## Story details")
for s in scheduled + unscheduled:
    w("")
    w(f"### {s['id']} {s['title']}")
    w("")
    w(f"*{s['priority']} | {s['points']} points | {s['sprint'] or 'not scheduled'} | {FEATS[s['feature']]['id']} {FEATS[s['feature']]['title']} | Source: {s['source']}*")
    w("")
    w(f"As {s['as_a']}, I want {s['i_want']}, so that {s['so_that']}.")
    w("")
    w("Acceptance criteria:")
    for a in s["acceptance"]:
        w(f"- {a}")
    w("")
    w(f"Traceability: use cases {ids(s['uc'])}; FR {ids(s['fr'])}; NFR {ids(s['nfr'])}; tests {ids(s['tests'])}.")
    w("")
    w("Suggested tasks (confirmed at sprint planning):")
    for i, t in enumerate(s["tasks"], 1):
        w(f"{i}. {t['title']} ({t['role']})")
w("")
w("## Won't have in this release")
w("")
for s in wont:
    w(f"- **{s['id']} {s['title']}.** {s['source']}")
w("")
w("## Traceability")
w("")
w("Every functional and non-functional requirement is delivered by at least one Must-have story. On the board, filter by the requirement's label "
  "(for example `label:FR-05`) to see the same list live.")
w("")
w("### Functional requirements to stories")
w("")
w("| FR | Requirement | Delivered by |")
w("|---|---|---|")
for code, text in REQ["fr"].items():
    by = [f"{s['id']}{'' if s['priority'] == 'Must' else ' (' + s['priority'] + ')'}" for s in STORIES if code in s["fr"]]
    w(f"| {code} | {text} | {', '.join(by)} |")
w("")
w("### Non-functional requirements to stories")
w("")
w("| NFR | Quality | Requirement | Delivered or verified by |")
w("|---|---|---|---|")
for code, q in REQ["nfr"].items():
    by = [f"{s['id']}{'' if s['priority'] == 'Must' else ' (' + s['priority'] + ')'}" for s in STORIES if code in s["nfr"]]
    w(f"| {code} | {q['quality']} | {q['text']} | {', '.join(by)} |")
w("")
w("### Use cases to stories")
w("")
w("| Use case | Name | Stories |")
w("|---|---|---|")
for code, name in REQ["use_cases"].items():
    w(f"| {code} | {name} | {', '.join(s['id'] for s in STORIES if code in s['uc'])} |")
w("")
w("### Acceptance tests to stories")
w("")
w("| Test | Scenario | Stories |")
w("|---|---|---|")
for code, text in REQ["acceptance_tests"].items():
    w(f"| {code} | {text} | {', '.join(s['id'] for s in STORIES if code in s['tests'])} |")
w("")
(KIT / "docs/agile").mkdir(parents=True, exist_ok=True)
(KIT / "docs/agile/product-backlog.md").write_text("\n".join(L) + "\n", encoding="utf-8")

# ------------------------------------------------------------------ sprint calendar
C = []
c = C.append
c("# Sprint calendar")
c("")
c(f"Start: {day(SPRINTS[0]['start'])}. Submission target: **{day(D['project']['submission_due'])}**. "
  f"Final cut-off: {day(D['project']['final_cutoff'])} (contingency only, no planned work). Times are US Central (America/Chicago).")
c("")
c("Sprints start on Monday and end on Sunday. Sprint 0 and Sprint 5 are one week; Sprint 3 runs three calendar weeks because it spans "
  "Christmas and New Year. The handbook asks for at least three sprints; this plan has four delivery sprints and a one-week release sprint "
  "after Sprint 0, each ending in a recorded demo for the Product Owner.")
c("")
c("| Sprint | Dates | Length | Goal | Milestones due |")
c("|---|---|---|---|---|")
for sp in SPRINTS:
    due = [m["id"] for m in D["milestones"] if sp["start"] <= m["due"] <= sp["end"]]
    c(f"| {sp['title']}: {sp['name']} | {rng(sp['start'], sp['end'])} | {sp['days']} days | {sp['goal']} | {', '.join(due) or 'None'} |")
c("")
c("## Milestones")
c("")
c("| Milestone | Due | What it means |")
c("|---|---|---|")
for m in D["milestones"]:
    c(f"| {m['title']} | {day(m['due'])} | {m['description']} |")
c("")
c("## Events")
c("")
c("Default rhythm (the team can move times, but keep the days so the board's ceremony checklists stay accurate):")
c("")
c("- **Sprint planning:** first Monday of the sprint, up to 2 hours (1 hour for one-week sprints). First half: choose the sprint backlog. Second half: break stories into tasks and assign them, then run `plan-sprint`.")
c("- **Weekly scrum:** Wednesdays, 30 minutes. Each person: what I finished, what I am doing next, what is blocking me. The handbook asks for about one scrum per week.")
c("- **Backlog refinement:** Thursday of the first week, 45 minutes. Make the next sprint's stories meet the Definition of Ready and re-estimate.")
c("- **Sprint review:** last day of the sprint. Record a demo of working software for the Product Owner (handbook requirement) and link the video in the ceremony issue.")
c("- **Retrospective:** straight after the review, 30 minutes. Record one or two improvements.")
c("")
c("| Date | Event |")
c("|---|---|")
rows = []
for sp in SPRINTS:
    if sp.get("planning"):
        rows.append((sp["planning"], f"{sp['title']} planning" + (" (start-up meeting first)" if sp["title"] == "Sprint 0" else "")))
    for d in sp.get("scrums", []):
        rows.append((d, f"{sp['title']} weekly scrum"))
    if sp.get("refinement"):
        rows.append((sp["refinement"], f"{sp['title']} backlog refinement"))
    if sp.get("review"):
        rows.append((sp["review"], f"{sp['title']} review with recorded demo, then retrospective"))
rows += [("2026-11-26", "Thanksgiving (reduced capacity 26 and 27 Nov)"),
         ("2026-12-25", "Christmas Day"), ("2027-01-01", "New Year's Day"),
         ("2027-01-17", "Feature freeze: only defects, documentation and evidence after this"),
         ("2027-01-18", "Martin Luther King Jr. Day"),
         ("2027-01-22", "Final video recorded"),
         ("2027-01-24", "Submission target"),
         ("2027-01-30", "Final cut-off (contingency only)")]
for d, e in sorted(rows):
    c(f"| {day(d)} | {e} |")
c("")
c("## Planned load")
c("")
c("| Sprint | Planned stories | Points |")
c("|---|---|---|")
for sp in SPRINTS:
    ss = [s for s in STORIES if s["sprint"] == sp["title"]]
    c(f"| {sp['title']} | {ids([s['id'] for s in ss])} | {sum(s['points'] for s in ss)} |")
c("")
c("These are first estimates. The plan assumes roughly 15 story points per team-week. Sprint 1's actual velocity is the first real "
  "measure: if it comes in lower, drop Should items first (US-07, US-08, US-28), then reduce the depth of US-26 and US-27, and "
  "protect the stories behind the final demo. If it comes in higher, pull US-07 or US-08 into Sprint 4.")
c("")
c("## Iteration field values")
c("")
c("The setup script creates these iterations. If GitHub refuses (older API), create an Iteration field named `Sprint` by hand with:")
c("")
c("| Title | Start date | Duration |")
c("|---|---|---|")
for sp in SPRINTS:
    c(f"| {sp['title']} | {sp['start']} | {sp['days']} days |")
c("")
(KIT / "docs/agile/sprint-calendar.md").write_text("\n".join(C) + "\n", encoding="utf-8")
print("written", len(L), "and", len(C), "lines")
