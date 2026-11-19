# Sprint 1 retrospective

**Date:** 19 November 2026  
**Attendees:** Olusanya Mafe / Siyabonga Jali  

## What went well

- The sprint goal was met, and all six stories (29 points) were merged by 18 November, well before the 29 November review.
- Writing the shared contracts first (US-18.1) meant the bank, the gateway, the audit trail and Vera were all built against one definition. Tests at the repository root fail if a service drifts from the bank's catalogue or the data schema.
- CI now proves the sprint goal on every pull request: lint, 714 tests including PostgreSQL, image builds scanned by Trivy, and the whole stack running Vera's scenarios, `verify-chain` and `completeness`.
- Design decisions were written down as they were made, in ADR-010 to ADR-014.

## What did not go well

- The two-track plan did not hold: US-17, US-19 and US-20 were planned for Siyabonga but built by Olusanya.
- The first Images run on `main` failed. OPA's health check needed `wget`, which the OPA image does not have, and our local test had used a stand-in image that hid the problem. It was fixed the same day in PR #131.
- Dependabot opened six pull requests on its first run, including a jump to Python 3.15 and a setuptools bump. Each one failed the Images check until we added ignore rules.
- The board did not show acceptance clearly. US-18 was closed straight after its merge, while the tasks of US-17, US-19 and US-20 closed automatically and their stories stayed open.

## What we will change in Sprint 2 (one or two items)

| Improvement | Owner | How we will know it worked |
|---|---|---|
| Merge only when every check is green, and make **stack (Docker Compose)** a required check on `main` | Olusanya Mafe | No red Images run on `main` during Sprint 2 |
| Close a story only after the Product Owner accepts it, with a closing comment that says so | Siyabonga Jali | Every Sprint 2 story is closed with an acceptance comment |

Follow-up on last sprint's improvement (both of us review and approve each pull request before it is merged): This was done partly
