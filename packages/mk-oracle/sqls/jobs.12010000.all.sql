-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section jobs
SELECT UPPER(decode(NVL(:IGNORE_DB_NAME, 0), 0, vp.NAME, iii.instance_name))
           || '|' || j.owner
           || '|' || j.job_name
           || '|' || j.state
           || '|' || ROUND((TRUNC(SYSDATE) + j.last_run_duration - TRUNC(SYSDATE)) * 86400)
           || '|' || j.run_count
           || '|' || j.enabled
           || '|' || NVL(j.next_run_date, to_date('1970-01-01', 'YYYY-MM-DD'))
           || '|' || NVL(j.schedule_name, '-')
           || '|' || jd.status
FROM v$instance iii, cdb_scheduler_jobs j
                         JOIN (
    SELECT vp.con_id,
           d.name || '|' || vp.name name
    FROM v$containers vp
             JOIN v$database d
                  ON 1=1
    WHERE d.cdb = 'YES' and vp.con_id <> 2
      AND d.database_role = 'PRIMARY'
      AND d.open_mode = 'READ WRITE'
    UNION ALL
    SELECT 0, name
    FROM v$database d
    WHERE d.database_role = 'PRIMARY'
      AND d.open_mode = 'READ WRITE') vp ON j.con_id = vp.con_id
                         LEFT OUTER JOIN (
    SELECT con_id,
           owner,
           job_name,
           max(log_id) log_id
    FROM cdb_scheduler_job_run_details dd
    GROUP BY con_id,
             owner,
             job_name
) jm
                                         ON jm.job_name = j.job_name
                                             AND jm.owner=j.owner
                                             AND jm.con_id = j.con_id
                         LEFT OUTER JOIN cdb_scheduler_job_run_details jd
                                         ON jd.con_id = jm.con_id
                                             AND jd.owner = jm.owner
                                             AND jd.job_name = jm.job_name
                                             AND jd.log_id = jm.log_id
WHERE NOT (j.auto_drop = 'TRUE' AND repeat_interval IS NULL)