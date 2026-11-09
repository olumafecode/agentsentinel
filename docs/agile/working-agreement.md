# Team working agreement

Fill in the blanks at the Sprint 0 start-up meeting and commit the result.

## Roles

The handbook expects the Product Owner and Scrum Master to write code as well as carry their role.

| Role | Person | GitHub username | Responsibilities |
|---|---|---|---|
| Product Owner | | | Owns the backlog order and sprint goals, writes and accepts stories, closes stories after checking acceptance criteria |
| Scrum Master | | | Runs the events, keeps the board accurate, removes blockers, runs `plan-sprint` |
| Code Owner(s) | | | Review and approve pull requests; listed in `.github/CODEOWNERS` |
| Developers | | | Everyone, including the two roles above |

## Meetings

| Event | When | Length | Notes saved in |
|---|---|---|---|
| Sprint planning | First Monday of each sprint, __:__ | up to 2 hours | `docs/agile/sprints/sprint-N/planning.md` |
| Weekly scrum | Wednesdays, __:__ | 30 minutes | `docs/agile/sprints/sprint-N/scrums.md` |
| Backlog refinement | Thursday of the first sprint week, __:__ | 45 minutes | Story issues on the board |
| Sprint review with recorded demo | Last day of each sprint, __:__ | 45 minutes | `docs/agile/sprints/sprint-N/review.md` |
| Retrospective | Straight after the review | 30 minutes | `docs/agile/sprints/sprint-N/retro.md` |

Times are US Central unless the team agrees otherwise. Meetings run to time; anything unresolved becomes a board item with an owner.

## How we communicate

- Day-to-day chat: ______ (for example Slack, Teams or WhatsApp). Decisions made in chat are copied onto the relevant issue.
- The board is the record of work. If it is not on the board, it is not planned.
- Reply to a review request within one working day.
- Say early when a task will slip; move it on the board and mention it at the next scrum.

## How we work on code

- Main is protected: pull request, one Code Owner approval and green CI before merge. No direct pushes.
- One task per pull request where possible; small pull requests are reviewed faster.
- At most two items in progress per person.
- Branch and commit conventions are in `CONTRIBUTING.md`.

## How we decide

- The Product Owner decides priority and accepts stories.
- The people doing the work decide how to do it and estimate it.
- Architecture choices that affect security boundaries, data storage, external services or deployment get an ADR.
- If we disagree and cannot settle it within the meeting, the Scrum Master time-boxes a short spike, and the Product Owner makes the call after it.

## Scope control

- New requests go to the backlog, not into the running sprint, unless they are critical defects or security blockers.
- If we fall behind, we drop Should and Could items first and protect the stories behind the final demo.
- Feature freeze: Sunday 17 January 2027. After that, only defects, documentation and evidence.
