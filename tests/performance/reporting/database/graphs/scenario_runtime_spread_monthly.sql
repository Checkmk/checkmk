-- Per-scenario runtime spread over a month: for the jobs of the 30 most recent
-- days with a run of the selected {{product_release}}, one value per job and
-- scenario (its mean runtime) for use with Metabase's box plot chart type. All
-- test_* scenarios. Reruns (_2, _3, ...) do not count.
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
