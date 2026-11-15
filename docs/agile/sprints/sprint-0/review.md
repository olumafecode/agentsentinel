# Sprint 0 review

**Date:**  15 November 2026
**Attendees:**  Olusanya Mafe / Siyabonga Jali
**Demo recording (for the Product Owner):** [link](https://drive.google.com/file/d/1sW8fiPDjaBRhgLzo_zunUWby6lbMpibt/view?usp=sharing)  

## Sprint goal

Board, repository rules, CI and the requirements baseline are in place, and milestone M1 is signed off.

Met? Yes / Partly / No, because: Yes. All Baseline for the Sprint gaol has been completed

## What the demo shows

Record your screen for about five minutes and walk through:

1. The Scrum board: Product backlog, Sprint board and Traceability views, and one story opened to show its tasks and requirement labels.
2. A merged pull request with a green `ci` check, and the ruleset that protects `main`.
3. The tests running on your machine: `py -m pytest -q`.
4. The baseline documents: requirements, one ADR, the architecture diagrams and the threat model.
5. The data schema rejecting a bad record (the schema tests).

## Stories

| Story | Points | Accepted by Product Owner? | Evidence (pull request, CI run, time in the recording) |
|---|---|---|---|
| US-12 Set up the Scrum board and product backlog | 2 | Accepted | https://github.com/users/olumafecode/projects/1 |
| US-13 Create the repository with review rules and templates | 3 | Accepted | https://github.com/olumafecode/agentsentinel/tree/main/.github/workflows |
| US-14 Commit the requirements and design baseline | 3 | Accepted | https://github.com/olumafecode/agentsentinel/actions/runs/42945853832 |
| US-10 Run automated checks on every pull request | 5 | Accepted | https://github.com/olumafecode/agentsentinel/actions/runs/42864153384 |
| US-15 Define the synthetic data schema | 2 | Accepted | https://github.com/olumafecode/agentsentinel/blob/main/data/synthetic/README.md |

**Velocity:** _15_ points accepted out of 15 planned.

## Milestone M1: requirements baseline accepted

- [ X ] Product Owner has read `docs/requirements/requirements.md`, the ADRs, the architecture and the threat model
- [ X ] Sign-off recorded in `docs/requirements/requirements.md` (the "Signed off" row and the change control table)
- [ X ] Milestone M1 closed on GitHub

Signed off by:  Siyabonga Jali
Date:  15 November 2026

## Board evidence

- Burn-up chart screenshot:
- Points-by-status chart screenshot:

## Backlog changes agreed

- Stories returned to the backlog or moved to Sprint 1:
- New stories or bugs added:
- Priority changes:
