-- Backend CPU history graph: average CPU usage per scenario across all jobs of
-- the selected {{product_release}} in the last 6 months. Backend scenarios only
-- (test_*, excluding UI). Divided by 100 for Metabase's percent
-- formatting.
SELECT
  j.job_name AS "Job Name",
  s.scenario_name AS "Scenario Name",
  AVG(m.measured_value) / 100 AS "Average CPU usage (%)"
FROM
  jobs j
  JOIN tests t ON j.job_id = t.job_id
  JOIN metrics m ON t.test_id = m.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
WHERE
  j.job_name LIKE CONCAT({{product_release}}, '-%')
  AND j.start_timestamp >= now() - INTERVAL '6 months'
  AND m.metric_name = 'cpu_info.cpu_percent'
  AND s.scenario_name LIKE 'test_%'
  AND s.scenario_name NOT LIKE 'test_performance_ui_%'
GROUP BY
  j.job_name,
  s.scenario_name
ORDER BY
  j.job_name ASC;
