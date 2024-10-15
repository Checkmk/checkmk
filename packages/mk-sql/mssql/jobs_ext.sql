-- This is example of a custom section
-- 1. place this file in <config-dir>/mssql folder, where config-dir is defined 
-- as either $MK_CONFIG or as "."
-- 2. Add in yaml file
--    sections:
--      - instance:
--      - jobs_ext:
-- run mk_sql -c config
-- Output Example:
-- <<<mssql_jobs_ext>>>
-- SQLEXPRESS_NAME
-- C:\Program Files\Microsoft SQL Server\MSSQL12.SQLEXPRESS_ID\MSSQL\DATA\master.mdf
-- C:\Program Files\Microsoft SQL Server\MSSQL12.SQLEXPRESS_ID\MSSQL\DATA\mastlog.ldf

select physical_name from sys.database_files
