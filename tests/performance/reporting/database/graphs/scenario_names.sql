-- Filter query: populates the {{scenario_name}} dashboard variable.
-- Lists the selectable performance scenarios (all test_* functions).
SELECT
  scenario_name
FROM
  scenarios
WHERE
  scenario_name LIKE 'test_%'
ORDER BY
  scenario_name ASC;
