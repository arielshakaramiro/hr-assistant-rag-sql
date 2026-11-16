-- Runs once on first DB init. Creates the read-only role the SQL agent uses.
-- The agent connects as hr_ro: SELECT only, no write/DDL. Table-level grants are
-- applied by the app after migrations (see app.db.grants), since tables don't exist yet here.
CREATE ROLE hr_ro WITH LOGIN PASSWORD 'hr_ro';
GRANT CONNECT ON DATABASE hr TO hr_ro;
-- Enable pgvector in the app database.
\connect hr
CREATE EXTENSION IF NOT EXISTS vector;
GRANT USAGE ON SCHEMA public TO hr_ro;
-- Default: future tables created by hr are SELECT-able by hr_ro (row scope enforced separately).
ALTER DEFAULT PRIVILEGES FOR ROLE hr IN SCHEMA public GRANT SELECT ON TABLES TO hr_ro;
