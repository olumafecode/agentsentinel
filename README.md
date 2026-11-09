# AgentSentinel

AgentSentinel sits between an AI banking agent and the bank's tools. Every action the agent tries to take is checked against identity, permissions, bank policy, data origin and risk before it can run, and is explained and recorded afterwards. MSSE capstone project; all data is synthetic.

| What | Where |
|---|---|
| **Scrum board** (product backlog, sprints, stories, tasks) | [AgentSentinel Scrum Board](https://github.com/users/olumafecode/projects/1) |
| Product backlog and traceability | [docs/agile/product-backlog.md](docs/agile/product-backlog.md) |
| Sprint calendar | [docs/agile/sprint-calendar.md](docs/agile/sprint-calendar.md) |
| Live demo | Added in Sprint 3 (US-11a) |
| Design and testing document | Added in Sprint 5 (US-11b) |
| Final demonstration video | Added in Sprint 5 (US-11b) |

## Team

| Role | Name | GitHub |
|---|---|---|
| Product Owner | | |
| Scrum Master | | |
| Code Owner(s) | | |
| Developers | | |

## How we work

Scrum, with Sprint 0 (one week), four delivery sprints and a release week between 9 November 2026 and 24 January 2027. Each sprint ends with a recorded demo for the Product Owner.

- [Board guide](docs/agile/board-guide.md): how the board is organized and how to plan a sprint
- [Definition of Ready and Done](docs/agile/definition-of-ready-and-done.md)
- [Working agreement](docs/agile/working-agreement.md)
- [Contributing](CONTRIBUTING.md): branches, commits, pull requests and reviews

## Repository layout

```
apps/              dashboard, banking agent (Vera), demo bank API
services/          sentinel gateway, risk engine, RAG service, approval service, audit service
policies/opa/      bank rules as code, with tests
data/              synthetic data and policy documents
ml/                training and evaluation
k8s/               Kubernetes profile
tests/             cross-service, end-to-end and scenario tests
docs/              requirements, architecture, ADRs, agile records, results
tools/board/       Scrum board setup script and backlog source
.github/           CI workflow, issue forms, pull request template, code owners
```

## Quickstart

Added in Sprint 1 (US-20): one `docker compose up` to run the stack locally.
