-- Memory drilldown graph: for the selected {{product_release}} and single
-- {{scenario_name}}, plots average memory usage per job and overlays fixed
-- reference baselines for releases 3.0.0/2.5.0/2.4.0/2.3.0 as extra columns. Each
-- baseline is the average of that release's 100 most recent measurements, skipping
-- the single most recent measurement (OFFSET 1) to avoid an in-progress or outlier build. The
-- per-job value and all baselines are divided by 100 for Metabase's percent
-- formatting, consistent with memory_history.sql.
WITH
  baseline300 AS (
    SELECT
      AVG(measured_value) AS baseline_memory_usage
    FROM
      (
        SELECT
          m.measured_value
        FROM
          jobs j
          JOIN tests t ON j.job_id = t.job_id
          JOIN metrics m ON t.test_id = m.test_id
          JOIN scenarios s ON t.scenario_id = s.scenario_id
        WHERE
          j.job_name LIKE '3.0.0-%'
          AND m.metric_name = 'memory_info.virtual_memory_percent'
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
      AVG(measured_value) AS baseline_memory_usage
    FROM
      (
        SELECT
          m.measured_value
        FROM
          jobs j
          JOIN tests t ON j.job_id = t.job_id
          JOIN metrics m ON t.test_id = m.test_id
          JOIN scenarios s ON t.scenario_id = s.scenario_id
        WHERE
          j.job_name LIKE '2.5.0-%'
          AND m.metric_name = 'memory_info.virtual_memory_percent'
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
      AVG(measured_value) AS baseline_memory_usage
    FROM
      (
        SELECT
          m.measured_value
        FROM
          jobs j
          JOIN tests t ON j.job_id = t.job_id
          JOIN metrics m ON t.test_id = m.test_id
          JOIN scenarios s ON t.scenario_id = s.scenario_id
        WHERE
          j.job_name LIKE '2.4.0-%'
          AND m.metric_name = 'memory_info.virtual_memory_percent'
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
      AVG(measured_value) AS baseline_memory_usage
    FROM
      (
        SELECT
          m.measured_value
        FROM
          jobs j
          JOIN tests t ON j.job_id = t.job_id
          JOIN metrics m ON t.test_id = m.test_id
          JOIN scenarios s ON t.scenario_id = s.scenario_id
        WHERE
          j.job_name LIKE '2.3.0-%'
          AND m.metric_name = 'memory_info.virtual_memory_percent'
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
  s.scenario_name AS "Scenario Name",
  AVG(m.measured_value) / 100 AS "average memory usage (%)",
  b300.baseline_memory_usage / 100 AS "3.0.0 baseline memory usage (%)",
  b250.baseline_memory_usage / 100 AS "2.5.0 baseline memory usage (%)",
  b240.baseline_memory_usage / 100 AS "2.4.0 baseline memory usage (%)",
  b230.baseline_memory_usage / 100 AS "2.3.0 baseline memory usage (%)"
FROM
  jobs j
  JOIN tests t ON j.job_id = t.job_id
  JOIN metrics m ON t.test_id = m.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
  CROSS JOIN baseline300 b300
  CROSS JOIN baseline250 b250
  CROSS JOIN baseline240 b240
  CROSS JOIN baseline230 b230
WHERE
  j.job_name LIKE CONCAT({{product_release}}, '-%')
  AND j.start_timestamp >= now() - INTERVAL '6 months'
  AND m.metric_name = 'memory_info.virtual_memory_percent'
  AND {{scenario_name}}
GROUP BY
  j.job_name,
  s.scenario_name,
  b300.baseline_memory_usage,
  b250.baseline_memory_usage,
  b240.baseline_memory_usage,
  b230.baseline_memory_usage
ORDER BY
  j.job_name ASC;
