-- Per-scenario runtime snapshot: mean test runtime per scenario for the 3 most
-- recent jobs of the selected {{product_release}} (latest builds only, not a time
-- window).
SELECT
  j.job_name AS "Job Name",
  s.scenario_name AS "Scenario Name",
  AVG(b.measured_value) AS "Time (s)" --single value by default, but calculate the average to be sure
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
  JOIN benchmarks b ON t.test_id = b.test_id
  JOIN scenarios s ON t.scenario_id = s.scenario_id
WHERE
  b.metric_name = 'mean'
  AND s.scenario_name LIKE 'test_%'
GROUP BY
  j.job_name,
  s.scenario_name
ORDER BY
  job_name DESC;
