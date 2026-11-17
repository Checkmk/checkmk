-- Per-scenario memory usage spread over a month: for the 30 newest jobs of the
-- selected {{product_release}}, one value per job and scenario (the average of
-- its samples) for use with Metabase's box plot chart type. All test_*
-- scenarios. Divided by 100 for Metabase's percent formatting. Only the first
-- run of a day counts, not its reruns (_2, _3, ...).
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
  AVG(m.measured_value) / 100 AS "Memory (%)"
FROM
  recent_jobs j
  JOIN tests t ON j.job_id = t.job_id
  JOIN metrics m ON t.test_id = m.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
WHERE
  m.metric_name = 'memory_info.virtual_memory_percent'
  AND s.scenario_name LIKE 'test_%'
GROUP BY
  j.job_id,
  s.scenario_name
ORDER BY
  s.scenario_name ASC;
