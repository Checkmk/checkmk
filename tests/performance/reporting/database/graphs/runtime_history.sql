-- Backend runtime history graph: average test runtime (average of the per-test
-- 'mean' benchmark, in seconds) per scenario across all jobs of the selected
-- {{product_release}} in the last 6 months. Backend scenarios only (test_*,
-- excluding UI).
SELECT
  j.job_name AS "Job Name",
  s.scenario_name AS "Scenario Name",
  AVG(bm.measured_value) AS "Time (s)"
FROM
  jobs j
  JOIN tests t ON j.job_id = t.job_id
  JOIN benchmarks bm ON t.test_id = bm.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
WHERE
  j.job_name LIKE CONCAT({{product_release}}, '-%')
  AND j.start_timestamp >= now() - INTERVAL '6 months'
  AND bm.metric_name = 'mean'
  AND s.scenario_name LIKE 'test_%'
  AND s.scenario_name NOT LIKE 'test_performance_ui_%'
GROUP BY
  j.job_name,
  s.scenario_name
ORDER BY
  j.job_name ASC;
