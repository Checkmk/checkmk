-- Per-scenario runtime spread in the latest job: for the newest job of the
-- selected {{product_release}}, the raw round times per scenario (stored by the
-- upload as data0, data1, ...) for use with Metabase's box plot chart type. All
-- test_* scenarios. Only the first run of a day counts, not its reruns (_2, _3,
-- ...).
WITH
  latest_job AS (
    SELECT
      job_id
    FROM
      jobs
    WHERE
      job_name LIKE {{product_release}} || '-%'
      AND job_name !~ '_[0-9]+$'
    ORDER BY
      start_timestamp DESC,
      job_id DESC
    LIMIT
      1
  )
SELECT
  s.scenario_name AS "Scenario Name",
  b.measured_value AS "Runtime (s)"
FROM
  latest_job j
  JOIN tests t ON j.job_id = t.job_id
  JOIN benchmarks b ON t.test_id = b.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
WHERE
  b.metric_name ~ '^data[0-9]+$'
  AND s.scenario_name LIKE 'test_%'
ORDER BY
  s.scenario_name ASC;
