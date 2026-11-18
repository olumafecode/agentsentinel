"""Creates and updates the audit schema (US-19.1).

Migrations are the numbered SQL files in ``sentinel_audit/migrations``. Each runs
once, in order, and is recorded in ``audit.schema_migrations``. Everything happens in
one transaction under a lock, so two migrators started together cannot clash and a
failed migration leaves the database as it was.

Before the SQL runs, the gateway's login role is created, or its password updated:
the password comes from configuration, so it cannot live in a SQL file.
"""

from importlib.resources import files

import psycopg
from psycopg import sql

GATEWAY_ROLE = "sentinel_gateway"
MIN_PASSWORD_LENGTH = 16
_MIGRATION_LOCK = 7_021_786_416_712_066_001


def pending_migrations() -> list[tuple[str, str]]:
    """Every migration as (version, SQL), in the order it must run."""
    folder = files("sentinel_audit").joinpath("migrations")
    scripts = sorted(
        (entry.name.removesuffix(".sql"), entry.read_text(encoding="utf-8"))
        for entry in folder.iterdir()
        if entry.name.endswith(".sql")
    )
    return scripts


def migrate(admin_url: str, gateway_password: str) -> list[str]:
    """Bring the audit schema up to date and return the versions applied now."""
    if len(gateway_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"the gateway's database password must be at least {MIN_PASSWORD_LENGTH} "
            "characters long"
        )
    applied_now = []
    with psycopg.connect(admin_url) as conn, conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK,))
        conn.execute("CREATE SCHEMA IF NOT EXISTS audit")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS audit.schema_migrations ("
            " version text PRIMARY KEY,"
            " applied_at timestamptz NOT NULL DEFAULT now())"
        )
        _ensure_gateway_role(conn, gateway_password)
        done = {
            row[0]
            for row in conn.execute("SELECT version FROM audit.schema_migrations")
        }
        for version, script in pending_migrations():
            if version in done:
                continue
            conn.execute(script)
            conn.execute(
                "INSERT INTO audit.schema_migrations (version) VALUES (%s)", (version,)
            )
            applied_now.append(version)
    return applied_now


def _ensure_gateway_role(conn: psycopg.Connection, password: str) -> None:
    exists = conn.execute(
        "SELECT 1 FROM pg_roles WHERE rolname = %s", (GATEWAY_ROLE,)
    ).fetchone()
    verb = "ALTER" if exists else "CREATE"
    conn.execute(
        sql.SQL(
            "{} ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}"
        ).format(sql.SQL(verb), sql.Identifier(GATEWAY_ROLE), sql.Literal(password))
    )
