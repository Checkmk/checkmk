-- Per-scenario runtime spread over a month: for the 30 newest jobs of the
-- selected {{product_release}}, one value per job and scenario (its mean
-- runtime) for use with Metabase's box plot chart type. All test_* scenarios.
-- Only the first run of a day counts, not its reruns (_2, _3, ...).
WITH
  recent_jobs AS (
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
      30
  )
SELECT
  s.scenario_name AS "Scenario Name",
  AVG(b.measured_value) AS "Runtime (s)"
FROM
  recent_jobs j
  JOIN tests t ON j.job_id = t.job_id
  JOIN benchmarks b ON t.test_id = b.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
WHERE
  b.metric_name = 'mean'
  AND s.scenario_name LIKE 'test_%'
GROUP BY
  j.job_id,
  s.scenario_name
ORDER BY
  s.scenario_name ASC;
