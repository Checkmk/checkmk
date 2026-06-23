-- PostgreSQL table creation script for Code Coverage Data Tables
--
-- Applied (idempotently) on every upload via tests.qa_metrics.db.apply_schema_file,
-- which runs the statements on an autocommit connection -- no explicit
-- transaction wrapper, mirroring the other qa_metrics schemas.

-- Per-module coverage of the most recent run. Rewritten in full on every
-- nightly upload, so it always reflects the latest state of the code base.
CREATE TABLE IF NOT EXISTS cmk_code_coverage_per_module (
    module_path VARCHAR PRIMARY KEY,
    covered_lines INTEGER NOT NULL,
    total_lines INTEGER NOT NULL,
    covered_functions INTEGER NOT NULL,
    total_functions INTEGER NOT NULL,
    commit_hash VARCHAR NOT NULL,
    commit_time TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Overall coverage history. One row per commit, never overwritten, so it can be
-- used to track the evolution of the total coverage over time.
CREATE TABLE IF NOT EXISTS cmk_code_coverage_total (
    commit_hash VARCHAR PRIMARY KEY,
    covered_lines INTEGER NOT NULL,
    total_lines INTEGER NOT NULL,
    covered_functions INTEGER NOT NULL,
    total_functions INTEGER NOT NULL,
    commit_time TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cmk_code_coverage_total_commit_time
    ON cmk_code_coverage_total(commit_time);

COMMENT ON TABLE cmk_code_coverage_per_module IS 'Per-module coverage of the most recent run; rewritten on every nightly upload';
COMMENT ON TABLE cmk_code_coverage_total IS 'Overall coverage history, one row per commit, never overwritten';

COMMENT ON COLUMN cmk_code_coverage_per_module.module_path IS 'Repository-relative path of the source module';
COMMENT ON COLUMN cmk_code_coverage_per_module.covered_lines IS 'Number of covered lines in this module';
COMMENT ON COLUMN cmk_code_coverage_per_module.total_lines IS 'Total number of lines in this module';
COMMENT ON COLUMN cmk_code_coverage_per_module.covered_functions IS 'Number of covered functions in this module';
COMMENT ON COLUMN cmk_code_coverage_per_module.total_functions IS 'Total number of functions in this module';
COMMENT ON COLUMN cmk_code_coverage_per_module.commit_hash IS 'check_mk repo git hash the coverage was measured on';
COMMENT ON COLUMN cmk_code_coverage_per_module.commit_time IS 'Committer time of the measured commit';

COMMENT ON COLUMN cmk_code_coverage_total.commit_hash IS 'check_mk repo git hash the coverage was measured on';
COMMENT ON COLUMN cmk_code_coverage_total.covered_lines IS 'Number of covered lines across all modules';
COMMENT ON COLUMN cmk_code_coverage_total.total_lines IS 'Total number of lines across all modules';
COMMENT ON COLUMN cmk_code_coverage_total.covered_functions IS 'Number of covered functions across all modules';
COMMENT ON COLUMN cmk_code_coverage_total.total_functions IS 'Total number of functions across all modules';
COMMENT ON COLUMN cmk_code_coverage_total.commit_time IS 'Committer time of the measured commit';
