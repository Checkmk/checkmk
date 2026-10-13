--performance user and database creation: to be run as "performance"
CREATE TABLE IF NOT EXISTS jobs(
    job_id SERIAL PRIMARY KEY,
    job_name TEXT UNIQUE NOT NULL,
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ NOT NULL,
    product_release TEXT NOT NULL,
    system_name TEXT NOT NULL,
    system_release TEXT NOT NULL,
    system_machine TEXT NOT NULL,
    host_name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scenarios(
    scenario_id SERIAL PRIMARY key,
    scenario_name TEXT UNIQUE NOT NULL,
    scenario_description TEXT
);
CREATE TABLE IF NOT EXISTS tests(
    test_id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(job_id) ON DELETE CASCADE,
    scenario_id INTEGER REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS benchmarks(
    test_id INTEGER REFERENCES tests(test_id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    measured_value       DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (test_id, metric_name)
);
CREATE TABLE IF NOT EXISTS metrics(
    test_id INTEGER REFERENCES tests(test_id) ON DELETE CASCADE,
    measured_at   TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    measured_value       DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (test_id, measured_at, metric_name)
);