-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

/*
Section rman: retrieves latest RMAN backup activities across three categories:
- Datafile Backups (Full / Incremental)
- Controlfile Backups
- Archived Log Backups
 */
/*$HINT_RMAN check_mk rman1 */
-- === Section 1: DATAFILE Backups (Full / Incremental) ===
SELECT UPPER(name),                                       -- DB name or instance name
       'COMPLETED',                                       -- Status marker
       TO_CHAR(COMPLETION_TIME, 'YYYY-mm-dd_HH24:MI:SS'), -- Backup completion start timestamp
       TO_CHAR(COMPLETION_TIME, 'YYYY-mm-dd_HH24:MI:SS'), -- Backup completion end timestamp
       NVL2(INCREMENTAL_LEVEL, 'DB_INCR', 'DB_FULL'),     -- If Incremental Level is NULL → DB_FULL
       INCREMENTAL_LEVEL,                                 -- Backup level (0 = full, >0 = incr)
       ROUND(((SYSDATE - COMPLETION_TIME) * 24 * 60), 0), -- Minutes since backup completed
       INCREMENTAL_CHANGE#                                -- Change# / SCN from backup
FROM (
         SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)) name,
                bd2.INCREMENTAL_LEVEL,
                bd2.INCREMENTAL_CHANGE#,
                MIN(bd2.COMPLETION_TIME)                                           COMPLETION_TIME
         FROM (
                  -- Get the latest backup time per file and backup level
                  SELECT bd.file#,
                         bd.INCREMENTAL_LEVEL,
                         MAX(bd.COMPLETION_TIME) COMPLETION_TIME
                  FROM v$backup_datafile bd
                           JOIN v$datafile_header dh
                                ON dh.file# = bd.file#
                  WHERE dh.status = 'ONLINE' -- Only consider ONLINE datafiles
                    AND dh.con_id <> 2       -- Exclude CDB$ROOT/seed PDB
                  GROUP BY bd.file#, bd.INCREMENTAL_LEVEL
              ) bd
                  JOIN v$backup_datafile bd2
                       ON bd2.file# = bd.file#
                           AND bd2.COMPLETION_TIME = bd.COMPLETION_TIME
                  JOIN v$database d
                       ON d.RESETLOGS_CHANGE# = bd2.RESETLOGS_CHANGE# -- Match DB incarnation
                  JOIN v$instance i ON 1 = 1
         GROUP BY UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)),
                  bd2.INCREMENTAL_LEVEL,
                  bd2.INCREMENTAL_CHANGE#
         ORDER BY name, bd2.INCREMENTAL_LEVEL
     )

UNION ALL
/*$HINT_RMAN check_mk rman2 */
-- === Section 2: CONTROLFILE Backups ===
SELECT name,
       'COMPLETED',                                       -- Status
       NULL,                                              -- No explicit "start time"
       TO_CHAR(CHECKPOINT_TIME, 'yyyy-mm-dd_hh24:mi:ss'), -- Controlfile backup checkpoint time
       'CONTROLFILE',                                     -- Backup type marker
       NULL,
       ROUND((SYSDATE - CHECKPOINT_TIME) * 24 * 60),      -- Minutes since backup
       0
FROM (
         SELECT UPPER(
                    DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)
                )                        name,
                MAX(bcd.CHECKPOINT_TIME) CHECKPOINT_TIME -- Latest controlfile checkpoint
         FROM v$database d
                  JOIN V$BACKUP_CONTROLFILE_DETAILS bcd
                       ON d.RESETLOGS_CHANGE# = bcd.RESETLOGS_CHANGE# -- Ensure correct incarnation
                  JOIN v$instance i ON 1 = 1
         GROUP BY UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name))
     )

UNION ALL
/*$HINT_RMAN check_mk rman3 */
-- === Section 3: ARCHIVELOG Backups ===
SELECT name,
       'COMPLETED',                                 -- Status
       TO_CHAR(SYSDATE, 'YYYY-mm-dd_HH24:MI:SS'),   -- Report generation timestamp
       TO_CHAR(completed, 'YYYY-mm-dd_HH24:MI:SS'), -- Last archivelog backup completion
       'ARCHIVELOG',                                -- Backup type marker
       NULL,
       ROUND((SYSDATE - completed) * 24 * 60, 0),   -- Minutes since last archivelog backup
       NULL
FROM (
         SELECT UPPER(
                    DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)
                )                      name,
                MAX(a.completion_time) completed,              -- Latest completed archivelog backup
                CASE WHEN a.backup_count > 0 THEN 1 ELSE 0 END -- Ensure backup exists
         FROM v$archived_log a,
              v$database d,
              v$instance i
         WHERE a.backup_count > 0 -- Only consider backed-up logs
           AND a.dest_id IN (
             SELECT b.dest_id
             FROM v$archive_dest b
             WHERE (b.target = 'PRIMARY' OR b.target = 'LOCAL') -- Include PRIMARY + LOCAL destinations
               AND b.SCHEDULE = 'ACTIVE'
                            )
         GROUP BY d.NAME, i.instance_name,
                  CASE WHEN a.backup_count > 0 THEN 1 ELSE 0 END
     )
