-- Filter query: populates the {{product_release}} dashboard variable.
-- Returns the distinct release prefixes (the part of job_name before the first
-- '-', e.g. 3.0.0, 2.5.0), newest first.
SELECT DISTINCT
  split_part(job_name, '-', 1) AS product_release
FROM
  jobs
ORDER BY
  product_release DESC;
