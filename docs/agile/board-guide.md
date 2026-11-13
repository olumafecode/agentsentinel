# Board guide

The Scrum board is a GitHub Project linked to this repository. It holds the product backlog, every sprint's backlog, each user story's tasks and their status. The handbook asks for a web-based Scrum board linked from the repository; the link is at the top of the README and the board also appears in the repository's **Projects** tab.

## What lives on the board

| Item | Label | What it is | Parent |
|---|---|---|---|
| Feature | `type:feature` | A group of related stories (F-01 to F-10) | None |
| User story | `type:story` | User value with acceptance criteria, story points, priority and requirement labels | Feature |
| Task | `type:task` | One piece of work inside a story, assigned to one person | Story |
| Bug | `type:bug` | A defect found in testing or review | Story it affects, if any |
| Ceremony checklist | `type:ceremony` | Planning, weekly scrums, review with recorded demo and retrospective for one sprint | None |

Stories are sub-issues of features, and tasks are sub-issues of stories, so every parent shows a progress bar. Each story also carries labels for the requirements it delivers: `FR-01` to `FR-20`, `NFR-01` to `NFR-14` and `UC-01` to `UC-12`. Filtering by one of those labels lists every story behind that requirement, which is the live traceability view.

## Fields

| Field | Values | Set by |
|---|---|---|
| Status | Backlog, Ready, In progress, In review, Done | Script at setup and planning, then the team and workflows |
| Sprint | Sprint 0 to Sprint 5, Contingency | Script, then the team at planning |
| Priority | Must, Should, Could, Won't (MoSCoW) | Product Owner |
| Story points | 1, 2, 3, 5, 8, 13 | Team at refinement or planning |
| Milestone | M1 to M7 (repository milestones) | Script; Product Owner if plans change |
| Assignees | Team members | Team at sprint planning |

What each status means:

- **Backlog:** in the product backlog, not in a sprint yet.
- **Ready:** planned into the current sprint and meets the Definition of Ready.
- **In progress:** someone is working on it. Limit: two items in progress per person.
- **In review:** a pull request is open (tasks) or the story is waiting for Product Owner acceptance (stories).
- **Done:** meets the Definition of Done. Tasks reach Done when their pull request merges. Stories reach Done only when the Product Owner moves them there after checking every acceptance criterion; the Auto-close issue workflow then closes the issue.

## Views to create (one time, about 10 minutes)

GitHub has no API for views, so create these by hand: open the board, click **+ New view**, choose the layout, then set the filter and options. Save each view.

| View name | Layout | Filter | Options |
|---|---|---|---|
| Product backlog | Table | `label:"type:story" -status:Done` | Group by Priority; sort by Sprint; show Status, Sprint, Story points, Milestone, Labels, Sub-issues progress |
| Sprint board | Board | `sprint:@current -label:"type:feature"` | Columns by Status; show Assignees and Story points on cards |
| Sprint backlog | Table | `sprint:@current label:"type:story"` | Turn on **Show hierarchy** so each story lists its tasks; show Status, Assignees, Sub-issues progress |
| Roadmap | Roadmap | `label:"type:story"` | Dates from Sprint; group by Milestone |
| Traceability | Table | `label:"type:story"` | Show Labels, Milestone, Status, Priority. Type `label:FR-05` (or any requirement) in the filter to trace it |
| My tasks | Table | `assignee:@me -status:Done` | Group by Sprint |

Rename the default "View 1" to **Product backlog** rather than leaving an extra view.

## Charts (Insights)

Click **Insights** at the top right of the board, then **New chart**:

1. **Sprint burn-up:** historical chart, filter `sprint:@current -label:"type:feature" -label:"type:ceremony"`. Shows work completed over the sprint.
2. **Points by status:** current chart, bar layout, filter `sprint:@current label:"type:story"`, X-axis Status, Y-axis Sum of Story points.

Take a screenshot of both charts at each sprint review and put it in the review notes; it is good evidence for the design and testing document.

## Workflows

Click **Workflows** at the top right of the board, next to **Insights**. For each workflow, click it, click **Edit**, choose the value, then **Save and turn on workflow**:

| Workflow | Setting | Why |
|---|---|---|
| Item closed | On, set Status to Done (on by default) | Merged pull requests close tasks |
| Pull request merged | On, set Status to Done (on by default) | Same as above for linked pull requests |
| Item reopened | On, set Status to In progress | Reopened work shows as active |
| Auto-add to project | On, repository agentsentinel, filter `is:issue` | New tasks and bugs created in the repository appear on the board. GitHub Free allows one auto-add workflow |
| Auto-add sub-issues to project | On (on by default) | New tasks created under a story appear on the board by themselves |
| Pull request linked to issue | On, set Status to In review | A task moves to In review when a pull request that closes it is opened, matching the status definitions above |
| Auto-close issue | On, when Status is set to Done | Keeps the closed state and the Done column in step. Only the Product Owner moves stories to Done |
| Code changes requested | Leave off | Applies to pull requests on the board; this board holds issues only |
| Code review approved | Leave off | Same as above |
| Item added to project | Leave off | The setup script sets Status itself; this workflow can overwrite it |
| Auto-archive items | Leave off | Keep every finished item visible for the grader |

The setup script replaced the Status options with Backlog, Ready, In progress, In review and Done. Every workflow that sets or checks a Status must have its value chosen again from the new list; otherwise it may still point at an old option (a red warning icon shows when it does).

Items added by either auto-add workflow arrive with no Status and no Sprint. Triage them at the next weekly scrum.

## Everyday flow for a task

1. On **Sprint board**, take a task in Ready, assign yourself and move it to In progress.
2. Create a branch from the task (issue page, **Development**, **Create a branch**) or by hand: `feature/US-18-4-signed-token`.
3. Commit with the story ID in the message: `feat(gateway): sign execution tokens (US-18.4)`.
4. Open a pull request. In the description write `Closes #<task number>` and `Part of #<story number>`, and fill in the template. The task moves to In review by itself.
5. CI must pass and a Code Owner must approve. Merge. The task closes and moves to Done.
6. When all of a story's tasks are done, move the story to In review. The Product Owner checks each acceptance criterion, ticks the boxes and moves the story to Done, which closes it.

Do not write `Closes #<story>` in a pull request; stories close only on Product Owner acceptance.

## Sprint planning, step by step

1. Note the previous sprint's velocity (story points of stories that reached Done).
2. Product Owner states the sprint goal and walks the top of **Product backlog**.
3. The team confirms each candidate meets the Definition of Ready, re-estimates if needed and stops at capacity.
4. Move any story you are deferring or pulling in by changing its Sprint field.
5. From the repository root, run (on Windows use `py` in place of `python`):
   ```
   python tools/board/setup_board.py --repo olumafecode/agentsentinel plan-sprint "Sprint 1"
   ```
   Add `--stories US-07,US-08` to plan a different set from the one in `backlog.json`. The command marks the stories Ready and creates their suggested tasks as sub-issues.
6. On **Sprint backlog**, edit, split or add tasks, and assign every task to a person.
7. Save notes in `docs/agile/sprints/sprint-N/planning.md` (template in `docs/agile/templates`), tick planning in the sprint's ceremony checklist and move that checklist to In progress.

## Ending a sprint

1. **Review:** record the demo of working software for the Product Owner and paste the video link into the ceremony checklist. The Product Owner accepts or rejects each story.
2. Unfinished stories go back to Backlog or move to the next sprint (change Status and Sprint; do not close them).
3. **Retrospective:** save one or two improvements in the retro notes.
4. Record velocity and the two chart screenshots in the review notes. Close the ceremony checklist.

## Bugs and new requests

- Bugs: use the **Bug** issue form. Add the bug as a sub-issue of the story it affects and set Priority. Critical defects and security blockers may enter the current sprint; everything else goes to the backlog.
- New ideas or requirement changes: create a **User story** issue with Status Backlog. The Product Owner prioritizes it at refinement. Changes that affect security boundaries, persistence, external services or deployment also get an ADR in `docs/adr`.

## Who can see the board

The repository and the board are both public. Anyone with the board link can see every feature, story, task and its status without signing in, including the quantic-grader account and faculty reviewers. Only people with write access to the repository can change the board.

Because the repository is public:

- Never commit secrets, API keys, `.env` files or real personal data. Keep secret scanning and push protection turned on (repository **Settings**, in the security section, called **Advanced Security** or **Code security** depending on your view).
- Anyone with a GitHub account can open an issue, and the auto-add workflow puts it on the board. Triage such issues at the weekly scrum and close any that are not project work.
