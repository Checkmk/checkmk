-- PostgreSQL table creation script for Code Coverage Data Tables

BEGIN;

CREATE TYPE cmk_git_branch_enum AS ENUM (
    'master', '2.4.0', '2.3.0'
);

CREATE TABLE IF NOT EXISTS cmk_components (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS cmk_test_run_types (
    id SERIAL PRIMARY KEY,
    makefile_target VARCHAR NOT NULL,
    alias VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS cmk_test_runs (
    id SERIAL PRIMARY KEY,
    test_run_type_id INTEGER NOT NULL REFERENCES cmk_test_run_types(id),
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    jenkins_build_id INTEGER,
    git_commit_hash VARCHAR NOT NULL,
    git_branch cmk_git_branch_enum NOT NULL,
    commit_time TIMESTAMP WITH TIME ZONE;
);

CREATE TABLE IF NOT EXISTS cmk_code_coverage_summary (
    test_run_id INTEGER PRIMARY KEY REFERENCES cmk_test_runs(id),
    lines_coverage_percent DECIMAL NOT NULL,
    functions_coverage_percent DECIMAL NOT NULL,
    covered_lines INTEGER,
    total_lines INTEGER,
    covered_functions INTEGER,
    total_functions INTEGER
);

CREATE TABLE IF NOT EXISTS cmk_source_code_modules (
    id SERIAL PRIMARY KEY,
    module_name VARCHAR NOT NULL,
    module_path VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS cmk_components_modules_mapping (
    id SERIAL PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES cmk_components(id),
    module_id INTEGER NOT NULL REFERENCES cmk_source_code_modules(id),
    UNIQUE(component_id, module_id)
);

CREATE TABLE IF NOT EXISTS cmk_module_code_coverage (
    id SERIAL PRIMARY KEY,
    test_run_id INTEGER NOT NULL REFERENCES cmk_test_runs(id),
    module_id INTEGER NOT NULL REFERENCES cmk_source_code_modules(id),
    lines_coverage_percent DECIMAL NOT NULL,
    functions_coverage_percent DECIMAL NOT NULL,
    covered_lines INTEGER NOT NULL,
    total_lines INTEGER NOT NULL,
    covered_functions INTEGER NOT NULL,
    total_functions INTEGER NOT NULL,
    UNIQUE(test_run_id, module_id)
);

CREATE INDEX idx_cmk_test_runs_type_id ON cmk_test_runs(test_run_type_id);
CREATE INDEX idx_cmk_test_runs_jenkins_build ON cmk_test_runs(jenkins_build_id);
CREATE INDEX idx_cmk_test_runs_git_branch ON cmk_test_runs(git_branch);
CREATE INDEX idx_cmk_test_runs_start_time ON cmk_test_runs(start_time);
CREATE INDEX idx_cmk_test_runs_end_time ON cmk_test_runs(end_time);
CREATE INDEX idx_cmk_components_name ON cmk_components(name);
CREATE INDEX idx_cmk_components_modules_mapping_component ON cmk_components_modules_mapping(component_id);
CREATE INDEX idx_cmk_components_modules_mapping_module ON cmk_components_modules_mapping(module_id);
CREATE INDEX idx_cmk_module_code_coverage_test_run ON cmk_module_code_coverage(test_run_id);
CREATE INDEX idx_cmk_module_code_coverage_module ON cmk_module_code_coverage(module_id);
CREATE INDEX idx_module_coverage_test_module ON cmk_module_code_coverage(test_run_id, module_id);
CREATE INDEX idx_source_modules_path ON cmk_source_code_modules(module_path);


COMMENT ON TABLE cmk_test_run_types IS 'Defines different types of test runs with their makefile targets';
COMMENT ON TABLE cmk_code_coverage_summary IS 'Code coverage metrics summary for each test run';
COMMENT ON TABLE cmk_source_code_modules IS 'Source code modules/components that can be tested';
COMMENT ON TABLE cmk_components_modules_mapping IS 'Mapping between components and source code modules';
COMMENT ON TABLE cmk_module_code_coverage IS 'Detailed code coverage metrics per module per test run';

COMMENT ON COLUMN cmk_test_run_types.makefile_target IS 'Target name in check_mk/tests/Makefile';
COMMENT ON COLUMN cmk_test_run_types.alias IS 'Descriptive code name of the test run type';
COMMENT ON COLUMN cmk_test_runs.git_commit_hash IS 'check_mk repo git hash';
COMMENT ON COLUMN cmk_code_coverage_summary.lines_coverage_percent IS 'Percentage of lines covered';
COMMENT ON COLUMN cmk_code_coverage_summary.functions_coverage_percent IS 'Percentage of functions covered';
COMMENT ON COLUMN cmk_module_code_coverage.lines_coverage_percent IS 'Percentage of lines covered for this specific module';
COMMENT ON COLUMN cmk_module_code_coverage.functions_coverage_percent IS 'Percentage of functions covered for this specific module';
COMMENT ON COLUMN cmk_module_code_coverage.covered_lines IS 'Number of lines covered in this module';
COMMENT ON COLUMN cmk_module_code_coverage.total_lines IS 'Total number of lines in this module';
COMMENT ON COLUMN cmk_module_code_coverage.covered_functions IS 'Number of functions covered in this module';
COMMENT ON COLUMN cmk_module_code_coverage.total_functions IS 'Total number of functions in this module';

COMMIT;
