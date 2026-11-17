-- Per-scenario CPU usage spread in the latest job: for the newest job of the
-- selected {{product_release}}, raw resource samples per scenario for use with
-- Metabase's box plot chart type. All test_* scenarios. Divided by 100 for
-- Metabase's percent formatting. Only the first run of a day counts, not its
-- reruns (_2, _3, ...).
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
  m.measured_value / 100 AS "CPU (%)"
FROM
  latest_job j
  JOIN tests t ON j.job_id = t.job_id
  JOIN metrics m ON t.test_id = m.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
WHERE
  m.metric_name = 'cpu_info.cpu_percent'
  AND s.scenario_name LIKE 'test_%'
ORDER BY
  s.scenario_name ASC;
