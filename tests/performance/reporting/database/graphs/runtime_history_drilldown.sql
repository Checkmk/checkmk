-- Runtime drilldown graph: for the selected {{product_release}} and single
-- {{scenario_name}}, plots average runtime (the per-test 'mean' benchmark, in
-- seconds) per job and overlays fixed reference baselines for releases
-- 3.0.0/2.5.0/2.4.0 as extra columns. Each baseline averages that release's 100
-- most recent jobs, skipping the most recent one (recency 1) to avoid an in-
-- progress or outlier build. Each job's values are averaged first, so every
-- build counts the same, however long it ran. Only the first run of a day
-- counts for the baselines, not its reruns (_2, _3, ...).
WITH
  job_values AS (
    SELECT
      SPLIT_PART(j.job_name, '-', 1) AS release,
      AVG(bm.measured_value) AS job_runtime,
      ROW_NUMBER() OVER (
        PARTITION BY
          SPLIT_PART(j.job_name, '-', 1)
        ORDER BY
          j.start_timestamp DESC,
          j.job_id DESC
      ) AS recency
    FROM
      jobs j
      JOIN tests t ON j.job_id = t.job_id
      JOIN benchmarks bm ON t.test_id = bm.test_id
      JOIN scenarios s ON t.scenario_id = s.scenario_id
    WHERE
      bm.metric_name = 'mean'
      AND {{scenario_name}}
      AND SPLIT_PART(j.job_name, '-', 1) IN ('3.0.0', '2.5.0', '2.4.0')
      AND j.job_name !~ '_[0-9]+$'
    GROUP BY
      j.job_id
  ),
  baselines AS (
    SELECT
      AVG(job_runtime) FILTER (WHERE release = '3.0.0') AS baseline300,
      AVG(job_runtime) FILTER (WHERE release = '2.5.0') AS baseline250,
      AVG(job_runtime) FILTER (WHERE release = '2.4.0') AS baseline240
    FROM
      job_values
    WHERE
      recency BETWEEN 2 AND 101
  )
SELECT
  j.job_name AS "Job Name",
  AVG(bm.measured_value) AS "duration (s)",
  b.baseline300 AS "3.0.0 baseline duration (s)",
  b.baseline250 AS "2.5.0 baseline duration (s)",
  b.baseline240 AS "2.4.0 baseline duration (s)"
FROM
  jobs j
  JOIN tests t ON j.job_id = t.job_id
  JOIN benchmarks bm ON t.test_id = bm.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
  CROSS JOIN baselines b
WHERE
  j.job_name LIKE CONCAT({{product_release}}, '-%')
  AND j.start_timestamp >= now() - INTERVAL '6 months'
  AND bm.metric_name = 'mean'
  AND {{scenario_name}}
GROUP BY
  j.job_name,
  s.scenario_name,
  b.baseline300,
  b.baseline250,
  b.baseline240
ORDER BY
  j.job_name ASC;
