# Sprint 0 weekly scrum and refinement

Sprint 0 runs 9 to 15 November 2026. Record what was actually said and the real date of each meeting.

## Weekly scrum

**Date: 11 November 2026**  
**Attendees: Olusanya Mafe / Siyabonga Jali**  

| Person | Finished since the sprint started | Doing next | Blockers |
|---|---|---|---|
|Olusanya Mafe | Board, views and workflows set up and linked from the README (US-12.1 to US-12.4); repository public with starter files (US-13.1, US-13.2); CI passing (US-10.1); first full pull request cycle with the smoke test (US-10.3, PR #80); requirements baseline, ADRs, architecture and threat model merged (US-14.1 to US-14.3, PR #81); synthetic data schema and labelling rules merged (US-15.1 to US-15.3, PRs #82 and #83)| Folder structure (US-13.3), pre-commit hooks (US-10.5), schema review (US-15.4), start-up meeting notes (US-12.5)| Permission issue Resolved: GitHub CLI not found in the VS Code terminal; board setup script error, fixed and re-run; CI failure from file permissions on Windows; rejected push to `main` and a merge conflict on the baseline branch

Board updated during the meeting: yes / no - updated during and after meeting  
Actions (owner, due):

- Siyabonga Jali: confirm the quarantine label and the near-limit refund band, by Thursday 12 November
- Olusanya Mafe: merge the folder structure (US-13.3) and pre-commit hooks (US-10.5), by Friday 13 November
- Olusanya Mafe: (Code Owner): complete the schema review (US-15.4), by Saturday 14 November
- Siyabonga Jali: read the baseline documents for the M1 sign-off, by Sunday 15 November

## Backlog refinement for Sprint 1

**Date: 16 November 2026**  
**Attendees: Olusanya Mafe / Siyabonga Jali**  

Sprint 1 candidates checked against the Definition of Ready:

| Story | Points | Ready? | Notes or re-estimate |
|---|---|---|---|
| US-16 Build the synthetic demo bank API | 3 | Yes | Uses the schema from US-15. (follow-up from the schema review)|
| US-17 Run Vera in scripted mode through the gateway only | 5 | Yes|Needs the contracts from US-18.1 and the tool list from US-16, so it starts in week 2. Live LLM mode stays in US-24 (Sprint 4) |
| US-18 Intercept every protected tool call at the gateway | 8 | Yes|At the 8-point limit. Do the contracts (US-18.1) first. If it runs over, split the signed token (US-18.4) into its own story |
| US-01 Keep Vera inside the current customer's data | 5 | Yes|Depends on US-18. The per-task tool list is temporary until OPA takes over in US-02a. Proves AT-01 and AT-02 |
| US-19 Write a hash-linked audit event for every decision | 5 | Yes|Needs PostgreSQL from US-20. The hash rule is already defined in "data/synthetic/README.md" |
| US-20 Run the whole stack with one Docker Compose command | 3 | Yes|Dockerfiles and the Compose file in week 1, because US-19 needs the database. Health endpoints and the CI image job can come last |

Decisions and changes to the backlog:

- No stories changed. All six meet the Definition of Ready, and the estimates stand at 29 points.
- Sprint 0 delivered 15 points in one week. Sprint 1 is two weeks with Thanksgiving (26 and 27 November), so 29 points is the most we can take.
- If the work is behind at the 25 November scrum, we will use the thanksgiving holiday to cover whats pending
