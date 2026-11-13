# Sprint calendar

Start: Mon 9 Nov 2026. Submission target: **Sun 24 Jan 2027**. Final cut-off: Sat 30 Jan 2027 (contingency only, no planned work). Times are US Central (America/Chicago).

Sprints start on Monday and end on Sunday. Sprint 0 and Sprint 5 are one week; Sprint 3 runs three calendar weeks because it spans Christmas and New Year. The handbook asks for at least three sprints; this plan has four delivery sprints and a one-week release sprint after Sprint 0, each ending in a recorded demo for the Product Owner.

| Sprint | Dates | Length | Goal | Milestones due |
|---|---|---|---|---|
| Sprint 0: Foundation | 9 Nov to 15 Nov 2026 | 7 days | Board, repository rules, CI and the requirements baseline are in place, and milestone M1 is signed off. | M1 |
| Sprint 1: First protected call | 16 Nov to 29 Nov 2026 | 14 days | One ALLOW and one BLOCK flow run end to end through the gateway and are fully audited (M2). | M2 |
| Sprint 2: Hybrid decision layer | 30 Nov to 13 Dec 2026 | 14 days | OPA policy, data-origin checks, machine learning risk scoring and policy-cited explanations work together (M3). | M3 |
| Sprint 3: Governance and platform | 14 Dec to 3 Jan 2027 | 21 days | Approvals, quarantine, incident timeline, dashboard, Kubernetes profile and public deployment are working (M4). | M4 |
| Sprint 4: Evaluation and hardening | 4 Jan to 17 Jan 2027 | 14 days | Security, utility, latency and resilience are measured against the targets; feature freeze at sprint end (M5, M6). | M5, M6 |
| Sprint 5: Release | 18 Jan to 24 Jan 2027 | 7 days | Submission package complete and submitted by Sunday 24 January (M7). | M7 |
| Contingency: Buffer only | 25 Jan to 30 Jan 2027 | 6 days | No planned work. Used only if the 24 January submission slips; final cut-off 30 January. | None |

## Milestones

| Milestone | Due | What it means |
|---|---|---|
| M1 Requirements baseline accepted | Sun 15 Nov 2026 | Use cases, FR, NFR, threat model and architecture aligned; board, repository and CI ready. |
| M2 First protected tool call | Sun 29 Nov 2026 | One allow and one block flow fully audited, running in Docker Compose. |
| M3 Hybrid decision layer | Sun 13 Dec 2026 | OPA, data provenance, machine learning risk and RAG explanation integrated. |
| M4 Human governance and incident operations | Sun 3 Jan 2027 | Approval, quarantine, dashboard and audit reconstruction working. |
| M5 Cloud-native evidence | Sun 17 Jan 2027 | CI/CD, public deployment, Kubernetes profile and observability demonstrated. |
| M6 Evaluation complete | Sun 17 Jan 2027 | Benchmark and scenario results, performance and resilience measured, defects closed. |
| M7 Submission ready | Sun 24 Jan 2027 | Repository, deployment URL, task board, design and testing document and final video submitted. |

## Events

Default rhythm (the team can move times, but keep the days so the board's ceremony checklists stay accurate):

- **Sprint planning:** first Monday of the sprint, up to 2 hours (1 hour for one-week sprints). First half: choose the sprint backlog. Second half: break stories into tasks and assign them, then run `plan-sprint`.
- **Weekly scrum:** Wednesdays, 30 minutes. Each person: what I finished, what I am doing next, what is blocking me. The handbook asks for about one scrum per week.
- **Backlog refinement:** Thursday of the first week, 45 minutes. Make the next sprint's stories meet the Definition of Ready and re-estimate.
- **Sprint review:** last day of the sprint. Record a demo of working software for the Product Owner (handbook requirement) and link the video in the ceremony issue.
- **Retrospective:** straight after the review, 30 minutes. Record one or two improvements.

| Date | Event |
|---|---|
| Mon 9 Nov 2026 | Sprint 0 planning (start-up meeting first) |
| Wed 11 Nov 2026 | Sprint 0 weekly scrum |
| Thu 12 Nov 2026 | Sprint 0 backlog refinement |
| Sun 15 Nov 2026 | Sprint 0 review with recorded demo, then retrospective |
| Mon 16 Nov 2026 | Sprint 1 planning |
| Wed 18 Nov 2026 | Sprint 1 weekly scrum |
| Thu 19 Nov 2026 | Sprint 1 backlog refinement |
| Wed 25 Nov 2026 | Sprint 1 weekly scrum |
| Thu 26 Nov 2026 | Thanksgiving (reduced capacity 26 and 27 Nov) |
| Sun 29 Nov 2026 | Sprint 1 review with recorded demo, then retrospective |
| Mon 30 Nov 2026 | Sprint 2 planning |
| Wed 2 Dec 2026 | Sprint 2 weekly scrum |
| Thu 3 Dec 2026 | Sprint 2 backlog refinement |
| Wed 9 Dec 2026 | Sprint 2 weekly scrum |
| Sun 13 Dec 2026 | Sprint 2 review with recorded demo, then retrospective |
| Mon 14 Dec 2026 | Sprint 3 planning |
| Wed 16 Dec 2026 | Sprint 3 weekly scrum |
| Thu 17 Dec 2026 | Sprint 3 backlog refinement |
| Wed 23 Dec 2026 | Sprint 3 weekly scrum |
| Fri 25 Dec 2026 | Christmas Day |
| Wed 30 Dec 2026 | Sprint 3 weekly scrum |
| Fri 1 Jan 2027 | New Year's Day |
| Sun 3 Jan 2027 | Sprint 3 review with recorded demo, then retrospective |
| Mon 4 Jan 2027 | Sprint 4 planning |
| Wed 6 Jan 2027 | Sprint 4 weekly scrum |
| Thu 7 Jan 2027 | Sprint 4 backlog refinement |
| Wed 13 Jan 2027 | Sprint 4 weekly scrum |
| Sun 17 Jan 2027 | Feature freeze: only defects, documentation and evidence after this |
| Sun 17 Jan 2027 | Sprint 4 review with recorded demo, then retrospective |
| Mon 18 Jan 2027 | Martin Luther King Jr. Day |
| Mon 18 Jan 2027 | Sprint 5 planning |
| Wed 20 Jan 2027 | Sprint 5 weekly scrum |
| Fri 22 Jan 2027 | Final video recorded |
| Sat 23 Jan 2027 | Sprint 5 review with recorded demo, then retrospective |
| Sun 24 Jan 2027 | Submission target |
| Sat 30 Jan 2027 | Final cut-off (contingency only) |

## Planned load

| Sprint | Planned stories | Points |
|---|---|---|
| Sprint 0 | US-12, US-13, US-14, US-10, US-15 | 15 |
| Sprint 1 | US-16, US-17, US-18, US-01, US-19, US-20 | 29 |
| Sprint 2 | US-02a, US-02b, US-21, US-04, US-06a | 34 |
| Sprint 3 | US-03, US-05, US-06b, US-22, US-23, US-11a | 36 |
| Sprint 4 | US-24, US-09, US-25, US-26, US-27, US-29 | 29 |
| Sprint 5 | US-11b | 5 |
| Contingency | None | 0 |

These are first estimates. The plan assumes roughly 15 story points per team-week. Sprint 1's actual velocity is the first real measure: if it comes in lower, drop Should items first (US-07, US-08, US-28), then reduce the depth of US-26 and US-27, and protect the stories behind the final demo. If it comes in higher, pull US-07 or US-08 into Sprint 4.

## Iteration field values

The setup script creates these iterations. If GitHub refuses (older API), create an Iteration field named `Sprint` by hand with:

| Title | Start date | Duration |
|---|---|---|
| Sprint 0 | 2026-11-09 | 7 days |
| Sprint 1 | 2026-11-16 | 14 days |
| Sprint 2 | 2026-11-30 | 14 days |
| Sprint 3 | 2026-12-14 | 21 days |
| Sprint 4 | 2027-01-04 | 14 days |
| Sprint 5 | 2027-01-18 | 7 days |
| Contingency | 2027-01-25 | 6 days |
