-- Per-scenario CPU snapshot: average CPU usage per scenario for the 3 most recent
-- jobs of the selected {{product_release}} (latest builds only, not a time window).
SELECT
  j.job_name AS "Job Name",
  s.scenario_name AS "Scenario Name",
  AVG(m.measured_value) / 100 AS "Average CPU usage (%)"
FROM
  (
    SELECT
      *
    FROM
      jobs
    WHERE
      job_name LIKE CONCAT({{product_release}}, '-%')
    ORDER BY
      start_timestamp DESC
    LIMIT
      3
  ) j
  JOIN tests t ON j.job_id = t.job_id
  JOIN metrics m ON t.test_id = m.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
WHERE
  m.metric_name = 'cpu_info.cpu_percent'
  AND s.scenario_name LIKE 'test_%'
GROUP BY
  j.job_name,
  s.scenario_name
ORDER BY
  j.job_name DESC;
