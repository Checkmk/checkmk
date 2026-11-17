-- CPU drilldown graph: for the selected {{product_release}} and single
-- {{scenario_name}}, plots average CPU usage per job and overlays fixed
-- reference baselines for releases 3.0.0/2.5.0/2.4.0 as extra columns. Each
-- baseline averages that release's 100 most recent jobs, skipping the most
-- recent one (recency 1) to avoid an in-progress or outlier build. Each job's
-- values are averaged first, so every build counts the same, however long it
-- ran. The per-job value and all baselines are divided by 100 for Metabase's
-- percent formatting, consistent with cpu_history.sql. Only the first run of a
-- day counts for the baselines, not its reruns (_2, _3, ...).
WITH
  job_values AS (
    SELECT
      SPLIT_PART(j.job_name, '-', 1) AS release,
      AVG(m.measured_value) AS job_cpu_usage,
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
      JOIN metrics m ON t.test_id = m.test_id
      JOIN scenarios s ON t.scenario_id = s.scenario_id
    WHERE
      m.metric_name = 'cpu_info.cpu_percent'
      AND {{scenario_name}}
      AND SPLIT_PART(j.job_name, '-', 1) IN ('3.0.0', '2.5.0', '2.4.0')
      AND j.job_name !~ '_[0-9]+$'
    GROUP BY
      j.job_id
  ),
  baselines AS (
    SELECT
      AVG(job_cpu_usage) FILTER (WHERE release = '3.0.0') AS baseline300,
      AVG(job_cpu_usage) FILTER (WHERE release = '2.5.0') AS baseline250,
      AVG(job_cpu_usage) FILTER (WHERE release = '2.4.0') AS baseline240
    FROM
      job_values
    WHERE
      recency BETWEEN 2 AND 101
  )
SELECT
  j.job_name AS "Job Name",
  s.scenario_name AS "Scenario Name",
  AVG(m.measured_value) / 100 AS "average CPU usage (%)",
  b.baseline300 / 100 AS "3.0.0 baseline CPU usage (%)",
  b.baseline250 / 100 AS "2.5.0 baseline CPU usage (%)",
  b.baseline240 / 100 AS "2.4.0 baseline CPU usage (%)"
FROM
  jobs j
  JOIN tests t ON j.job_id = t.job_id
  JOIN metrics m ON t.test_id = m.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
  CROSS JOIN baselines b
WHERE
  j.job_name LIKE CONCAT({{product_release}}, '-%')
  AND j.start_timestamp >= now() - INTERVAL '6 months'
  AND m.metric_name = 'cpu_info.cpu_percent'
  AND {{scenario_name}}
GROUP BY
  j.job_name,
  s.scenario_name,
  b.baseline300,
  b.baseline250,
  b.baseline240
ORDER BY
  j.job_name ASC;
