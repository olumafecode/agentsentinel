# ADR-010: Shared contracts and HMAC-signed single-use execution tokens

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-18 |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-01, FR-08, FR-09; NFR-01, NFR-03 |
| Stories | US-18 (US-18.1, US-18.4), US-16, US-17, US-29 |

## Context

ADR-001 makes the Sentinel Gateway the only path to a protected tool, and says the gateway issues a signed single-use execution token for each allowed action. Two things had to be settled before the first services were built.

First, the gateway, Vera and every protected tool exchange the same messages. If each service defined its own copy, the copies would drift and a field renamed in one place would break another at run time.

Second, the token format. The bank must be able to prove that a call was allowed by the gateway, for exactly these arguments, recently, and only once. The agent must not be able to create, change or reuse a token.

## Decision

- The request and decision contracts and the token code live in one shared package, `libs/sentinel-contracts`, imported by every service. A test at the repository root checks that the contracts match `data/synthetic/models.py`.
- A token is `v1.<claims>.<signature>`. The claims are the token ID, correlation ID, tool name, SHA-256 of the canonical JSON arguments, customer, issuer, audience, issue time and expiry. The signature is HMAC-SHA256 with a key shared by the gateway and the bank (`EXECUTION_TOKEN_KEY`, at least 32 bytes). Vera never receives the key.
- Tokens live 60 seconds by default and never more than 300.
- A tool accepts a token only when the signature, issuer, audience, tool and argument hash all match and the token has not expired. It then records the token ID, and a second use is refused.
- The token travels in the `X-Execution-Token` header. A service without a valid key refuses to start.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| A copy of the contracts in each service | Rejected. Copies drift, and the failure shows up only at run time. |
| JSON Web Tokens through a library such as PyJWT | Workable. Rejected for now because the standard library covers what is needed, the format is short enough to audit by eye, and JWT's algorithm options are a known source of mistakes. |
| Asymmetric signatures (Ed25519): the gateway signs, the bank only verifies | Stronger, because the bank could not mint tokens itself. Deferred: it adds key-pair management and a dependency. The `v1` prefix lets a `v2` format replace HMAC later without changing callers. |
| Network rules only (mutual TLS or NetworkPolicy), no token | Rejected. It proves which service called, not that this exact call was allowed. NetworkPolicy is still added in the Kubernetes profile (US-23) as a second layer. |

## Consequences

What we gain:

- One definition of every message, checked against the synthetic schema on every pull request.
- A captured token is useless after one use, after 60 seconds, against another tool, or with any argument changed.
- No new dependency: the token code uses only the Python standard library.

What it costs:

- Anyone holding the shared key can mint tokens, so the bank is trusted not to misuse it. The key must stay out of the repository and out of Vera's configuration.
- The record of used tokens is in memory, per process. A tool that runs more than one replica must share it, for example in PostgreSQL, before it scales out.
- Rotating the key needs the gateway and the bank to restart together.
