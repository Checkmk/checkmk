-- Runtime drilldown graph: for the selected {{product_release}} and single
-- {{scenario_name}}, plots average runtime per job and overlays fixed reference
-- baselines for releases 3.0.0/2.5.0/2.4.0/2.3.0 as extra columns. Each baseline
-- is the average of that release's 100 most recent mean-runtime measurements,
-- skipping the single most recent measurement (OFFSET 1) to avoid an in-progress or outlier build.
WITH
  baseline300 AS (
    SELECT
      AVG(measured_value) AS baseline_runtime
    FROM
      (
        SELECT
          bm.measured_value
        FROM
          jobs j
          JOIN tests t ON j.job_id = t.job_id
          JOIN benchmarks bm ON t.test_id = bm.test_id
          JOIN scenarios s ON t.scenario_id = s.scenario_id
        WHERE
          j.job_name LIKE '3.0.0-%'
          AND bm.metric_name = 'mean'
          AND {{scenario_name}}
        ORDER BY
          j.start_timestamp DESC
        OFFSET
          1
        LIMIT
          100
      )
  ),
  baseline250 AS (
    SELECT
      AVG(measured_value) AS baseline_runtime
    FROM
      (
        SELECT
          bm.measured_value
        FROM
          jobs j
          JOIN tests t ON j.job_id = t.job_id
          JOIN benchmarks bm ON t.test_id = bm.test_id
          JOIN scenarios s ON t.scenario_id = s.scenario_id
        WHERE
          j.job_name LIKE '2.5.0-%'
          AND bm.metric_name = 'mean'
          AND {{scenario_name}}
        ORDER BY
          j.start_timestamp DESC
        OFFSET
          1
        LIMIT
          100
      )
  ),
  baseline240 AS (
    SELECT
      AVG(measured_value) AS baseline_runtime
    FROM
      (
        SELECT
          bm.measured_value
        FROM
          jobs j
          JOIN tests t ON j.job_id = t.job_id
          JOIN benchmarks bm ON t.test_id = bm.test_id
          JOIN scenarios s ON t.scenario_id = s.scenario_id
        WHERE
          j.job_name LIKE '2.4.0-%'
          AND bm.metric_name = 'mean'
          AND {{scenario_name}}
        ORDER BY
          j.start_timestamp DESC
        OFFSET
          1
        LIMIT
          100
      )
  ),
  baseline230 AS (
    SELECT
      AVG(measured_value) AS baseline_runtime
    FROM
      (
        SELECT
          bm.measured_value
        FROM
          jobs j
          JOIN tests t ON j.job_id = t.job_id
          JOIN benchmarks bm ON t.test_id = bm.test_id
          JOIN scenarios s ON t.scenario_id = s.scenario_id
        WHERE
          j.job_name LIKE '2.3.0-%'
          AND bm.metric_name = 'mean'
          AND {{scenario_name}}
        ORDER BY
          j.start_timestamp DESC
        OFFSET
          1
        LIMIT
          100
      )
  )
SELECT
  j.job_name AS "Job Name",
  AVG(bm.measured_value) AS "duration (s)",
  b300.baseline_runtime AS "3.0.0 baseline duration (s)",
  b250.baseline_runtime AS "2.5.0 baseline duration (s)",
  b240.baseline_runtime AS "2.4.0 baseline duration (s)",
  b230.baseline_runtime AS "2.3.0 baseline duration (s)"
FROM
  jobs j
  JOIN tests t ON j.job_id = t.job_id
  JOIN benchmarks bm ON t.test_id = bm.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
  CROSS JOIN baseline300 b300
  CROSS JOIN baseline250 b250
  CROSS JOIN baseline240 b240
  CROSS JOIN baseline230 b230
WHERE
  j.job_name LIKE CONCAT({{product_release}}, '-%')
  AND j.start_timestamp >= now() - INTERVAL '6 months'
  AND bm.metric_name = 'mean'
  AND {{scenario_name}}
GROUP BY
  j.job_name,
  s.scenario_name,
  b300.baseline_runtime,
  b250.baseline_runtime,
  b240.baseline_runtime,
  b230.baseline_runtime
ORDER BY
  j.job_name ASC;
