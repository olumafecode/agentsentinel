# Contributing

## Before you start

Pick a task from the **Sprint board** view, assign yourself and move it to In progress. Work that is not on the board is not planned; add it as a task or bug first.

## Branches

`<type>/<story>-<task>-<short-name>`, for example:

- `feature/US-18-4-signed-token`
- `fix/US-02b-1-taint-match`
- `docs/US-14-2-adr-002`

Or use **Create a branch** in the task's Development panel, which links the branch to the task.

## Commits

[Conventional Commits](https://www.conventionalcommits.org) with the task ID at the end:

```
feat(gateway): sign single-use execution tokens (US-18.4)
test(policy): boundary cases for refund threshold (US-02a.3)
docs(adr): record OPA decision (US-14.2)
```

Types: `feat`, `fix`, `test`, `docs`, `refactor`, `ci`, `build`, `chore`.

## Pull requests

- One task per pull request where you can.
- Fill in the template. Write `Closes #<task number>` so the task closes on merge, and `Part of #<story number>` to link the story. Never close a story from a pull request; the Product Owner closes stories after acceptance.
- Add the FR and NFR labels the change touches.
- CI (`ci` check) must be green and a Code Owner must approve. Main is protected; nobody pushes to it directly.
- Reviewers reply within one working day. Review for correctness, tests, security (trust boundaries, secrets, deny by default) and readability.

## Code and data rules

- Synthetic data only. Never commit real names, account numbers, credentials or API keys. Use `.env` locally and commit `.env.example`.
- Pin dependency versions.
- Security-critical modules (gateway decisions, policy client, token signing, audit chain) need tests for both the allowed and the denied path.
- Changes to security boundaries, persistence, external services or deployment need an ADR in `docs/adr`.
