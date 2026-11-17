# Sprint 0 retrospective

**Date: 15 November 2026**  
**Attendees: Olusanya Mafe / Siyabonga Jali**  

## What went well
All five Sprint 0 stories (15 of 15 points) were accepted, and milestone M1 was signed off on 15 November.
- The quality gate works: `main` accepts changes only through a pull request with a passing `ci` check, and CI caught two real problems before they reached `main`.
- We completed our first full cycle of task, branch, pull request, CI and merge with the smoke test (US-10.3), and used the same flow for every task after it.
- The requirements baseline, eight ADRs, architecture, threat model and synthetic data schema were committed and reviewed. The schema review was approved, with its follow-ups covered by existing stories.
- The open policy settings were confirmed within two days (200.00 USD automatic refund limit, 5,000.00 USD hard cap, quarantine after three blocked actions in 10 minutes), so Sprint 2 starts from agreed values.

## What did not go well

- Setting up the tools on Windows cost time early in the sprint: the GitHub CLI was not found in the VS Code terminal, and some commands were run from the wrong folder.
- The board setup script stopped partway with "Content already exists in this project" and had to be fixed and re-run.
- Before the `main` ruleset existed, changes were committed straight to `main`. Later a push to `main` was rejected, and the baseline branch hit a merge conflict that took extra time to resolve.
- CI failed twice for avoidable reasons: two scripts lost their executable flag on Windows (Ruff rule EXE001), which was due to extra indentation.

## What we will change in Sprint 1 (one or two items)

| Improvement | Owner | How we will know it worked |
|---|---|---|
|Every pull request is reviewed by both team member before it is approved and subsequently merged |Olusanya Mafe / Siyabonga Jali |Joint review and approval |
