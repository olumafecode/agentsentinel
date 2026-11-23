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
| Product Owner | Siyabonga Jali | Siyabonga169 |
| Scrum Master | Olusanya Mafe | Olumafecode |
| Code Owner(s) | Olusanya Mafe | Olumafecode |
| Developers | Olusanya Mafe / Siyabonga Jali | Olumafecode / Siyabonga169 |

## How we work

Scrum, with Sprint 0 (one week), four delivery sprints and a release week between 9 November 2026 and 24 January 2027. Each sprint ends with a recorded demo for the Product Owner.

- [Board guide](docs/agile/board-guide.md): how the board is organized and how to plan a sprint
- [Definition of Ready and Done](docs/agile/definition-of-ready-and-done.md)
- [Working agreement](docs/agile/working-agreement.md)
- [Contributing](CONTRIBUTING.md): branches, commits, pull requests and reviews

## Repository layout

```
apps/              dashboard, banking agent (Vera), demo bank API
libs/              shared code used by more than one service (sentinel-contracts)
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

Run the whole stack with Docker Compose (US-20). You need Docker Desktop and Python. From the repository root:

```
py tools/dev/make_env.py
docker compose up --build --wait
```

The first command writes `.env` with random keys and passwords; git ignores it. The second builds the images, starts PostgreSQL, OPA, the demo bank and the Sentinel Gateway, and returns once every health check passes. Then:

```
docker compose run --rm vera                    # Vera's scenarios through the gateway
docker compose run --rm audit verify-chain      # the audit hash chain is intact
docker compose run --rm audit completeness      # every action is fully audited
docker compose down                             # stop; add -v to delete the database
```

| Service | Address on your machine |
|---|---|
| Sentinel Gateway | http://localhost:8000/docs |
| Demo bank API | http://localhost:8001/docs |
| OPA | http://localhost:8181/health |

Each service's README explains how to run it on its own. For tests and the pre-commit hooks:

```
py -m pip install -r requirements-dev.txt
py -m pytest -q
```

The PostgreSQL tests are skipped unless `AUDIT_TEST_DATABASE_URL` is set; see `services/audit-service/README.md`. The bank policy tests and the acceptance tests need the `opa` command and are skipped without it; see `policies/opa/README.md`. CI runs all of them, builds and scans every image, and runs the Compose stack end to end on every pull request.
