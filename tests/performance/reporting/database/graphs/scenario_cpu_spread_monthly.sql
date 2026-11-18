-- Per-scenario CPU usage spread over a month: for the jobs of the 30 most
-- recent days with a run of the selected {{product_release}}, one value per job
-- and scenario (the average of its samples) for use with Metabase's box plot
-- chart type. All test_* scenarios. Divided by 100 for Metabase's percent
-- formatting. Reruns (_2, _3, ...) do not count.
WITH
  recent_jobs AS (
    SELECT
      job_id
    FROM
      (
        SELECT
          job_id,
          DENSE_RANK() OVER (
            ORDER BY
              start_timestamp::date DESC
          ) AS day_recency
        FROM
          jobs
        WHERE
          job_name LIKE {{product_release}} || '-%'
          AND job_name !~ '_[0-9]+$'
      ) ranked_jobs
    WHERE
      day_recency <= 30
  )
SELECT
  s.scenario_name AS "Scenario Name",
  AVG(m.measured_value) / 100 AS "CPU (%)"
FROM
  recent_jobs j
  JOIN tests t ON j.job_id = t.job_id
  JOIN metrics m ON t.test_id = m.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
WHERE
  m.metric_name = 'cpu_info.cpu_percent'
  AND s.scenario_name LIKE 'test_%'
GROUP BY
  j.job_id,
  s.scenario_name
ORDER BY
  s.scenario_name ASC;
