-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section rman: retrieves the latest RMAN backup activity for a database
/*${HINT_RMAN} check_mk rman1 */
-- === Section 1: Check latest DATAFILE backups (Full or Incremental) ===
SELECT UPPER(name),                                       -- Database name or instance name
       'COMPLETED',                                       -- Backup status
       TO_CHAR(COMPLETION_TIME, 'YYYY-mm-dd_HH24:MI:SS'), -- Completion time (as start time for reporting)
       TO_CHAR(COMPLETION_TIME, 'YYYY-mm-dd_HH24:MI:SS'), -- Same completion time as end time
       NVL2(INCREMENTAL_LEVEL, 'DB_INCR', 'DB_FULL'),     -- Distinguish between Incremental and Full backup
       INCREMENTAL_LEVEL,                                 -- Incremental level (0 = full, >0 = incremental)
       ROUND(((SYSDATE - COMPLETION_TIME) * 24 * 60), 0), -- Elapsed minutes since backup completed
       INCREMENTAL_CHANGE#                                -- SCN of incremental backup
FROM (SELECT UPPER(
                     DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)
             )                        name,
             bd2.INCREMENTAL_LEVEL,
             bd2.INCREMENTAL_CHANGE#,
             MIN(bd2.COMPLETION_TIME) COMPLETION_TIME -- Earliest completion time for grouping
      FROM (
               -- Get the latest backup time per file and level
               SELECT bd.file#,
                      bd.INCREMENTAL_LEVEL,
                      MAX(bd.COMPLETION_TIME) COMPLETION_TIME
               FROM v$backup_datafile bd
                        JOIN v$datafile_header dh
                             ON dh.file# = bd.file#
               WHERE dh.status = 'ONLINE' -- Only consider ONLINE datafiles
               GROUP BY bd.file#, bd.INCREMENTAL_LEVEL
           ) bd
               JOIN v$backup_datafile bd2
                    ON bd2.file# = bd.file#
                        AND bd2.COMPLETION_TIME = bd.COMPLETION_TIME
               JOIN v$database d
                    ON d.RESETLOGS_CHANGE# = bd2.RESETLOGS_CHANGE# -- Ensure correct incarnation
               JOIN v$instance i
                    ON 1 = 1
      GROUP BY UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)),
               bd2.INCREMENTAL_LEVEL,
               bd2.INCREMENTAL_CHANGE#
      ORDER BY name, bd2.INCREMENTAL_LEVEL
     )

UNION ALL
/*${HINT_RMAN} check_mk rman2 */
-- === Section 2: Check latest CONTROLFILE backup ===
SELECT name,
       'COMPLETED',                                       -- Backup status
       NULL,                                              -- No explicit start time
       TO_CHAR(CHECKPOINT_TIME, 'yyyy-mm-dd_hh24:mi:ss'), -- Latest checkpoint time for controlfile backup
       'CONTROLFILE',                                     -- Backup type
       NULL,
       ROUND((SYSDATE - CHECKPOINT_TIME) * 24 * 60),      -- Elapsed minutes since controlfile backup
       0
FROM (SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)) name,
             MAX(bcd.CHECKPOINT_TIME)                                           CHECKPOINT_TIME -- Latest controlfile checkpoint
      FROM v$database d
               JOIN v$backup_controlfile_details bcd
                    ON d.RESETLOGS_CHANGE# = bcd.RESETLOGS_CHANGE# -- Ensure correct database incarnation
               JOIN v$instance i
                    ON 1 = 1
      GROUP BY UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name))
     )

UNION ALL
/*${HINT_RMAN} check_mk rman3 */
-- === Section 3: Check latest ARCHIVELOG backup ===
SELECT name,
       'COMPLETED',                                 -- Backup status
       TO_CHAR(SYSDATE, 'YYYY-mm-dd_HH24:MI:SS'),   -- Report generation time
       TO_CHAR(completed, 'YYYY-mm-dd_HH24:MI:SS'), -- Latest archived log backup completion
       'ARCHIVELOG',                                -- Backup type
       NULL,
       ROUND((SYSDATE - completed) * 24 * 60, 0),   -- Elapsed minutes since archivelog backup
       NULL
FROM (SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)) name,
             MAX(a.completion_time)                                             completed, -- Most recent archivelog backup
             CASE WHEN a.backup_count > 0 THEN 1 ELSE 0 END                                -- Ensure at least one backup exists
      FROM v$archived_log a,
           v$database d,
           v$instance i
      WHERE a.backup_count > 0 -- Only archived logs that were backed up
        AND a.dest_id IN (SELECT b.dest_id
                          FROM v$archive_dest b
                          WHERE b.target = 'PRIMARY' -- Only primary destinations
                            AND b.SCHEDULE = 'ACTIVE' -- Only active destinations
                         )
      GROUP BY d.NAME, i.instance_name, CASE WHEN a.backup_count > 0 THEN 1 ELSE 0 END
     )
