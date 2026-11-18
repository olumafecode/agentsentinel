-- Audit trail tables, append-only rules and the gateway's privileges (US-19.1, US-19.4).
-- Applied by `python -m sentinel_audit migrate`, which creates the schema, the
-- schema_migrations table and the sentinel_gateway role before this file runs.

-- Every action Vera proposed that was well formed enough to store.
CREATE TABLE audit.tool_calls (
    correlation_id    text PRIMARY KEY
        CHECK (correlation_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    session_id        text NOT NULL CHECK (session_id ~ '^SES-[0-9]{8}$'),
    agent_id          text NOT NULL CHECK (agent_id ~ '^AGT-[0-9]{3}$'),
    customer_scope    text NOT NULL CHECK (customer_scope ~ '^CUS-[0-9]{6}$'),
    task_type         text NOT NULL,
    tool_name         text NOT NULL,
    arguments         jsonb NOT NULL,
    provenance_labels jsonb NOT NULL,
    requested_at      timestamptz NOT NULL,
    recorded_at       timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE audit.tool_calls IS 'Proposed tool calls (ToolCall entity), one per correlation ID';

-- The hash-linked chain. position is the place in the chain; event_id is derived from it.
CREATE TABLE audit.events (
    position            bigint PRIMARY KEY CHECK (position BETWEEN 1 AND 999999),
    event_id            text NOT NULL UNIQUE
        CHECK (event_id = 'EVT-' || lpad(position::text, 6, '0')),
    correlation_id      text NOT NULL
        CHECK (correlation_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    event_type          text NOT NULL CHECK (event_type IN (
        'action_received', 'policy_evaluated', 'risk_assessed', 'decision_made',
        'approval_requested', 'approval_decided', 'action_executed', 'action_stopped',
        'agent_quarantined', 'explanation_generated'
    )),
    actor               text NOT NULL CHECK (length(actor) BETWEEN 3 AND 40),
    decision            text CHECK (decision IN ('ALLOW', 'HUMAN_REVIEW', 'BLOCK', 'QUARANTINE')),
    policy_version      text CHECK (policy_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
    model_version       text CHECK (model_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
    payload             jsonb NOT NULL,
    created_at          timestamptz NOT NULL,
    previous_event_hash text NOT NULL CHECK (previous_event_hash ~ '^[0-9a-f]{64}$'),
    event_hash          text NOT NULL UNIQUE CHECK (event_hash ~ '^[0-9a-f]{64}$')
);
COMMENT ON TABLE audit.events IS 'Hash-linked audit events (AuditEvent entity); hash rule in data/synthetic/README.md';
CREATE INDEX events_by_correlation ON audit.events (correlation_id, position);

-- Append-only for everyone, owner included. Changing a row means disabling this
-- trigger first, which only the table owner can do, and verify-chain still finds it.
CREATE FUNCTION audit.refuse_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit records are append-only: % on %.% is not allowed',
        TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END;
$$;

CREATE TRIGGER events_append_only BEFORE UPDATE OR DELETE ON audit.events
    FOR EACH ROW EXECUTE FUNCTION audit.refuse_change();
CREATE TRIGGER events_no_truncate BEFORE TRUNCATE ON audit.events
    FOR EACH STATEMENT EXECUTE FUNCTION audit.refuse_change();
CREATE TRIGGER tool_calls_append_only BEFORE UPDATE OR DELETE ON audit.tool_calls
    FOR EACH ROW EXECUTE FUNCTION audit.refuse_change();
CREATE TRIGGER tool_calls_no_truncate BEFORE TRUNCATE ON audit.tool_calls
    FOR EACH STATEMENT EXECUTE FUNCTION audit.refuse_change();

-- The gateway may add and read audit rows, nothing more (ADR-005).
REVOKE ALL ON SCHEMA audit FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA audit FROM PUBLIC;
GRANT USAGE ON SCHEMA audit TO sentinel_gateway;
GRANT SELECT, INSERT ON audit.events, audit.tool_calls TO sentinel_gateway;
