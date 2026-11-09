# Scrum board setup

`setup_board.py` builds the AgentSentinel Scrum board in GitHub Projects from `backlog.json`, and creates each sprint's tasks at sprint planning.

## One-time setup (about 10 minutes, plus 10 minutes in the browser)

1. Install the GitHub CLI from https://cli.github.com and sign in with the project scope:
   ```
   gh auth login
   gh auth refresh -s project
   ```
2. See what will be created (changes nothing):
   ```
   python tools/board/setup_board.py --repo OWNER/agentsentinel setup --dry-run
   ```
3. Create everything. Add `--create-repo` if the repository does not exist yet, and `--invite-grader` to give quantic-grader access:
   ```
   python tools/board/setup_board.py --repo OWNER/agentsentinel setup --create-repo --invite-grader
   ```
   It pauses one second after each change to stay inside GitHub's rate limits, so it takes about four minutes. If GitHub does slow it down, it waits and retries on its own.
4. In the browser, create the views and turn on the workflows listed in `docs/agile/board-guide.md`.
5. Paste the board link into the README in place of `ADD-BOARD-LINK`.
6. Commit the state file `tools/board/.board-state-OWNER-agentsentinel.json`. It holds the board's IDs (nothing secret) so any teammate can run the planning command.

## What gets created

| Item | Count |
|---|---|
| Labels | 5 item types, FR-01 to FR-20, NFR-01 to NFR-14, UC-01 to UC-12 |
| Milestones | M1 to M7 with due dates |
| Project | Public, linked to the repository, with Status, Priority, Story points and Sprint fields |
| Sprints | Sprint 0 to Sprint 5 and Contingency, with real dates |
| Issues | 10 features, 6 sprint ceremony checklists, 37 user stories, and the Sprint 0 tasks |

## At each sprint planning

```
python tools/board/setup_board.py --repo OWNER/agentsentinel plan-sprint "Sprint 1"
```

This marks that sprint's stories Ready and creates their suggested tasks as sub-issues. To plan a different set of stories, list them: `--stories US-07,US-16`. Then edit, split and assign the tasks on the board.

## Re-running and fixing problems

- Every command can be re-run safely. Anything already created is skipped.
- **"lacks the 'project' scope":** run `gh auth refresh -s project`.
- **Rate limit messages:** the script waits and retries. If it stops, run the same command again.
- **Sprint field could not be created:** create an Iteration field named `Sprint` by hand with the dates in `docs/agile/sprint-calendar.md`, then re-run setup to fill in each item's sprint.
- **Status options could not be renamed:** the script falls back to GitHub's Todo, In Progress and Done. Rename them in the project settings to Backlog, Ready, In progress, In review and Done if you want the full flow.

## Changing the plan

The board is the working copy once it exists. `backlog.json` is the baseline the script and the backlog document read. If you change stories in `backlog.json` (for example new acceptance criteria or a new story), run `python tools/board/build_docs.py` to regenerate `docs/agile/product-backlog.md` and `docs/agile/sprint-calendar.md`, and re-run setup to create any new stories.
