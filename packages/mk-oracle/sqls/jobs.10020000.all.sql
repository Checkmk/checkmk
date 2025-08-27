-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section jobs: retrieves information about DBA Scheduler jobs in the primary, open database
SELECT UPPER(
           DECODE(NVL(:IGNORE_DB_NAME, 0), 0, vd.NAME, i.instance_name)
       )                         AS db_or_instance,   -- If :IGNORE_DB_NAME = 0 → use DB name, else use instance name
       j.owner,                                       -- Schema/owner of the job
       j.job_name,                                    -- Name of the scheduler job
       j.state,                                       -- Current state (e.g., ENABLED, DISABLED, RUNNING)
       ROUND(
           (TRUNC(SYSDATE) + j.last_run_duration - TRUNC(SYSDATE)) * 86400
       )                         AS last_run_seconds, -- Duration of the last job run, converted to seconds
       j.run_count,                                   -- Number of times the job has executed
       j.enabled,                                     -- Whether the job is enabled (TRUE/FALSE)
       TO_CHAR(
           NVL(j.next_run_date,
               TO_DATE('1970-01-01', 'YYYY-MM-DD'))
       )                         AS next_run_date,    -- Next scheduled run (defaulted if null)
       NVL(j.schedule_name, '-') AS schedule_name,    -- Schedule name associated with the job (or '-' if none)
       jd.status                                      -- Status of the most recent run (e.g., SUCCEEDED, FAILED, STOPPED)
FROM dba_scheduler_jobs j -- Data dictionary view of all Scheduler jobs
         JOIN v$database vd ON 1 = 1 -- Database metadata (name, role, mode)
         JOIN v$instance i ON 1 = 1 -- Instance metadata (instance name)
         LEFT JOIN (
    -- Subquery: find latest run log ID for each job
    SELECT owner, job_name, MAX(log_id) log_id
    FROM dba_scheduler_job_run_details dd
    GROUP BY owner, job_name
                   ) jm
                   ON jm.job_name = j.job_name
                       AND jm.owner = j.owner
         LEFT JOIN dba_scheduler_job_run_details jd
                   ON jd.owner = jm.owner
                       AND jd.job_name = jm.job_name
                       AND jd.log_id = jm.log_id
WHERE vd.database_role = 'PRIMARY' -- Only include jobs from the primary database
  AND vd.open_mode = 'READ WRITE'  -- Only include jobs from open databases
  AND NOT (j.auto_drop = 'TRUE' AND repeat_interval IS NULL) -- Exclude one-time jobs that auto-drop