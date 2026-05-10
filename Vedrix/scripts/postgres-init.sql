-- PostgreSQL Security Configuration
-- Run this script to set up secure database access
-- Usage: psql -U postgres -d vedrix_prod -f postgres-init.sql

-- ── Create Application User (Least Privilege) ───────────────────────────────────
-- Create a dedicated user for the application with limited privileges

CREATE USER vedrix_app WITH PASSWORD 'CHANGE_ME_IN_PRODUCTION';
ALTER USER vedrix_app WITH CONNECTION LIMIT 20;
ALTER USER vedrix_app VALID UNTIL '2099-01-01';

-- ── Create Read-Only User (for reporting/analytics) ────────────────────────────
CREATE USER vedrix_readonly WITH PASSWORD 'CHANGE_ME_READONLY';
ALTER USER vedrix_readonly VALID UNTIL '2099-01-01';

-- ── Create Tables ────────────────────────────────────────────────────────────────
-- Tables will be created by the application

-- ── Grant Permissions ────────────────────────────────────────────────────────────
-- App user gets full access to application tables
GRANT CONNECT ON DATABASE vedrix_prod TO vedrix_app;

GRANT USAGE ON SCHEMA public TO vedrix_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO vedrix_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO vedrix_app;

-- Readonly user gets only SELECT
GRANT CONNECT ON DATABASE vedrix_prod TO vedrix_readonly;
GRANT USAGE ON SCHEMA public TO vedrix_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO vedrix_readonly;

-- ── Row-Level Security (Optional - for multi-tenant) ────────────────────────────
-- Enable RLS on tables if needed for multi-tenant isolation
-- ALTER TABLE interview_session ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "user_is_owner" ON interview_session
--     FOR ALL USING (candidate_id = current_setting('app.user_id')::int);

-- ── Set Default Privileges ─────────────────────────────────────────────────────
-- Future tables will automatically get permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vedrix_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO vedrix_readonly;

-- ── Create Audit Table ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    user_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET
);

-- Only superuser can write, app user can read
REVOKE INSERT, UPDATE, DELETE ON audit_log FROM vedrix_app;
GRANT SELECT ON audit_log TO vedrix_app;
GRANT INSERT ON audit_log TO vedrix_readonly;

-- ── Create Function for Audit Logging ────────────────────────────────────────
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation, new_values)
        VALUES (TG_TABLE_NAME, 'INSERT', to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, old_values, new_values)
        VALUES (TG_TABLE_NAME, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, old_values)
        VALUES (TG_TABLE_NAME, 'DELETE', to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ── Enable Audit Triggers (Optional) ──────────────────────────────────────────
-- Uncomment to enable audit logging on specific tables
-- CREATE TRIGGER audit_user AFTER INSERT OR UPDATE OR DELETE ON user
--     FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- ── Security Settings ─────────────────────────────────────────────────────────
-- Disable public schema access
REVOKE ALL ON DATABASE vedrix_prod FROM PUBLIC;

-- Set session timeout (30 minutes)
SET session_timeout = '30min';

-- Enable SSL (configured in postgresql.conf)
-- ssl = on
-- ssl_cert_file = 'server.crt'
-- ssl_key_file = 'server.key'

-- Log configuration (in postgresql.conf)
-- log_connections = on
-- log_disconnections = on
-- log_statement = 'ddl'
-- log_min_duration_statement = 1000

-- ── Create Index for Audit Log ───────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_audit_log_table_timestamp
    ON audit_log (table_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_timestamp
    ON audit_log (user_id, timestamp DESC);

-- ── Grant Superuser for Migrations (temporary) ────────────────────────────────
-- After running migrations, revoke superuser:
-- ALTER USER vedrix_app NOSUPERUSER;

-- Print current configuration
\echo '=== PostgreSQL Security Configuration Complete ==='
\echo 'Users created:'
\du vedrix_app
\du vedrix_readonly