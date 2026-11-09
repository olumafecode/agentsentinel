# Definition of Ready and Definition of Done

Agreed at the Sprint 0 start-up meeting. Change it only at a retrospective, and note the change in that retro's notes.

## Definition of Ready (a story can enter a sprint when)

- [ ] The user value is clear: role, capability and benefit are written as a user story.
- [ ] Acceptance criteria are written as Given, When, Then and each one can be tested.
- [ ] Use cases, FRs, NFRs and acceptance tests are linked (labels on the board and the traceability table in the story).
- [ ] Dependencies are identified and either done or planned earlier in the same sprint.
- [ ] Security implications are noted (what could go wrong, which trust boundary it touches).
- [ ] Data or API contracts it needs exist or are part of the story.
- [ ] It is estimated and small enough to finish in one sprint (8 points or fewer; split anything larger).

## Definition of Done for a task

- [ ] Code is merged to main through a pull request reviewed by a Code Owner.
- [ ] CI is green: lint, unit tests, policy tests and scans.
- [ ] Tests for the change are added or updated.
- [ ] No secrets, credentials or real personal data are committed.

## Definition of Done for a user story

- [ ] All of its tasks are Done.
- [ ] Every acceptance criterion passes and is linked to test evidence (test name, CI run or recording).
- [ ] Unit, policy and integration tests cover the new behavior; security-critical modules aim for 80% coverage or more.
- [ ] API contracts, docs and ADRs affected by the story are updated.
- [ ] Container images build, and the behavior is shown running where it applies (Docker Compose, public demo or Kubernetes profile).
- [ ] The Product Owner has accepted it and closed the issue.

## Definition of Done for a sprint

- [ ] Sprint review held and a demo of working software recorded for the Product Owner; video linked in the ceremony checklist.
- [ ] Retrospective held with one or two recorded improvements.
- [ ] Velocity, burn-up chart and points-by-status chart captured in the review notes.
- [ ] Unfinished stories returned to the backlog or moved to the next sprint, not closed.

## Definition of Done for the release (Sprint 5)

- [ ] Public demo URL works and is in the README.
- [ ] README quickstart runs on a clean machine.
- [ ] Design and testing document complete, with measured results in place of targets.
- [ ] Traceability from story to requirement, test and evidence complete.
- [ ] 15 to 20 minute video recorded with every team member on camera.
- [ ] Repository shared with quantic-grader; release tagged v1.0.0; submitted by Sunday 24 January 2027.
