-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section jobs
SELECT UPPER(decode(NVL(:IGNORE_DB_NAME, 0), 0, vd.NAME, i.instance_name))
           || '|' || j.owner
           || '|' || j.job_name
           || '|' || j.state
           || '|' || ROUND((TRUNC(SYSDATE) + j.last_run_duration - TRUNC(SYSDATE)) * 86400)
           || '|' || j.run_count
           || '|' || j.enabled
           || '|' || NVL(j.next_run_date, to_date('1970-01-01', 'YYYY-MM-DD'))
           || '|' || NVL(j.schedule_name, '-')
           || '|' || jd.status
FROM dba_scheduler_jobs j
         JOIN v$database vd on 1 = 1
         JOIN v$instance i on 1 = 1
         LEFT OUTER JOIN (
    SELECT owner,
           job_name,
           MAX(log_id) log_id
    FROM dba_scheduler_job_run_details dd
    GROUP BY owner,
             job_name
) jm ON jm.job_name = j.job_name
    AND jm.owner=j.owner
         LEFT OUTER JOIN dba_scheduler_job_run_details jd ON jd.owner = jm.owner
    AND jd.job_name = jm.job_name
    AND jd.log_id = jm.log_id
WHERE vd.database_role = 'PRIMARY'
  AND vd.open_mode = 'READ WRITE'
  AND NOT (j.auto_drop = 'TRUE' AND repeat_interval IS NULL)
