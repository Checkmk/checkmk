-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section jobs: retrieves Oracle Scheduler job information across all PDBs in a multitenant database
SELECT vp.instance_name,                              -- Instance name (or DB name depending on :IGNORE_DB_NAME)
       vp.container_name,                             -- Pluggable database (PDB) name
       j.owner,                                       -- Schema/owner of the job
       j.job_name,                                    -- Name of the scheduler job
       j.state,                                       -- Current job state (ENABLED, DISABLED, RUNNING, etc.)
       ROUND((TRUNC(SYSDATE) + j.last_run_duration - TRUNC(SYSDATE)) * 86400)
                                 AS last_run_seconds, -- Duration of the last job run in seconds
       j.run_count,                                   -- Number of times the job has executed
       j.enabled,                                     -- Whether the job is enabled (TRUE/FALSE)
       TO_CHAR(
           NVL(j.next_run_date,
               TO_DATE('1970-01-01', 'YYYY-MM-DD'))
       )                         AS next_run_date,    -- Next scheduled run date/time (defaulted if null)
       NVL(j.schedule_name, '-') AS schedule_name,    -- Associated schedule name (or '-' if none)
       jd.status                                      -- Status of the most recent run (SUCCEEDED, FAILED, STOPPED, etc.)
FROM cdb_scheduler_jobs j -- CDB view of scheduler jobs across all PDBs
         JOIN (
    -- Subquery: maps container ID to instance and container names
    SELECT c.con_id,
           UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0),
                        1, d.NAME, -- If :IGNORE_DB_NAME = 1 → show DB name
                        i.instance_name -- Else → show instance name
                 )) AS instance_name,
           c.name   AS container_name -- PDB name
    FROM v$containers c
             JOIN v$database d ON 1 = 1
             LEFT JOIN v$instance i
                       ON i.con_id = d.con_id
    WHERE d.cdb = 'YES'               -- Must be a multitenant container database
      AND c.con_id <> 2               -- Exclude seed PDB (con_id = 2)
      AND d.database_role = 'PRIMARY' -- Only primary DB (exclude standby)
      AND d.open_mode = 'READ WRITE'  -- Only open databases
    UNION ALL
    -- Handles non-CDB-like representation (fallback case)
    SELECT 0, d.name, c.name
    FROM v$database d
             JOIN v$instance i
                  ON i.con_id = d.con_id
             LEFT JOIN v$containers c
                       ON c.dbid = d.dbid
    WHERE d.database_role = 'PRIMARY'
      AND d.open_mode = 'READ WRITE'
              ) vp
              ON j.con_id = vp.con_id
         LEFT JOIN (
    -- Subquery: get latest run log ID per job
    SELECT con_id,
           owner,
           job_name,
           MAX(log_id) log_id
    FROM cdb_scheduler_job_run_details dd
    GROUP BY con_id, owner, job_name
                   ) jm
                   ON jm.job_name = j.job_name
                       AND jm.owner = j.owner
                       AND jm.con_id = j.con_id
         LEFT JOIN cdb_scheduler_job_run_details jd
                   ON jd.con_id = jm.con_id
                       AND jd.owner = jm.owner
                       AND jd.job_name = jm.job_name
                       AND jd.log_id = jm.log_id
WHERE NOT (j.auto_drop = 'TRUE' AND repeat_interval IS NULL) -- Exclude one-time auto-drop jobs