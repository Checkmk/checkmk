-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section undostat
SELECT /*$HINT_RMAN check_mk rman1 */ UPPER(name)
        || '|'|| 'COMPLETED'
        || '|'|| TO_CHAR(COMPLETION_TIME, 'YYYY-mm-dd_HH24:MI:SS')
        || '|'|| TO_CHAR(COMPLETION_TIME, 'YYYY-mm-dd_HH24:MI:SS')
        || '|'|| NVL2(INCREMENTAL_LEVEL, 'DB_INCR', 'DB_FULL') -- If LEVEL is null, then DB_FULL
        || '|'|| INCREMENTAL_LEVEL
        || '|'|| ROUND(((SYSDATE-COMPLETION_TIME) * 24 * 60), 0)
        || '|'|| INCREMENTAL_CHANGE#
    FROM (
        SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)) name,
            bd2.INCREMENTAL_LEVEL,
            bd2.INCREMENTAL_CHANGE#,
            MIN(bd2.COMPLETION_TIME) COMPLETION_TIME
            FROM (
                SELECT bd.file#,
                    bd.INCREMENTAL_LEVEL,
                    MAX(bd.COMPLETION_TIME) COMPLETION_TIME
                    FROM v$backup_datafile bd
                    JOIN v$datafile_header dh ON dh.file# = bd.file#
                    WHERE dh.status = 'ONLINE' AND dh.con_id <> 2
                    GROUP BY bd.file#, bd.INCREMENTAL_LEVEL
            ) bd
            JOIN v$backup_datafile bd2
                ON bd2.file# = bd.file# AND bd2.COMPLETION_TIME = bd.COMPLETION_TIME
            JOIN v$database d
                ON d.RESETLOGS_CHANGE# = bd2.RESETLOGS_CHANGE#
            JOIN v$instance i
                ON 1=1
            GROUP BY UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)),
                bd2.INCREMENTAL_LEVEL,
                bd2.INCREMENTAL_CHANGE#
            ORDER BY name, bd2.INCREMENTAL_LEVEL
    )
UNION ALL
SELECT /*$HINT_RMAN check_mk rman2 */ name
        || '|' || 'COMPLETED'
        || '|'
        || '|' || TO_CHAR(CHECKPOINT_TIME, 'yyyy-mm-dd_hh24:mi:ss')
        || '|' || 'CONTROLFILE'
        || '|'
        || '|' || ROUND((SYSDATE - CHECKPOINT_TIME) * 24 * 60)
        || '|' || '0'
    FROM (
        SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)) name,
            MAX(bcd.CHECKPOINT_TIME) CHECKPOINT_TIME
            FROM v$database d
            JOIN V$BACKUP_CONTROLFILE_DETAILS bcd
                ON d.RESETLOGS_CHANGE# = bcd.RESETLOGS_CHANGE#
            JOIN v$instance i ON 1=1
            GROUP BY UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name))
     )
UNION ALL
SELECT /*$HINT_RMAN check_mk rman3 */ name
        || '|COMPLETED'
        || '|'|| TO_CHAR(SYSDATE, 'YYYY-mm-dd_HH24:MI:SS')
        || '|'|| TO_CHAR(completed, 'YYYY-mm-dd_HH24:MI:SS')
        || '|ARCHIVELOG||'
        || ROUND((SYSDATE - completed)*24*60,0)
        || '|'
    FROM (
         SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)) name
              , MAX(a.completion_time) completed
              , CASE WHEN a.backup_count > 0 THEN 1 ELSE 0 END
            FROM v$archived_log a, v$database d, v$instance i
            WHERE a.backup_count > 0
                AND
                    a.dest_id IN(
                        SELECT b.dest_id
                        FROM v$archive_dest b
                        WHERE (b.target = 'PRIMARY' OR b.target = 'LOCAL') -- LOCAL is valid nur for 2.2
                            AND b.SCHEDULE = 'ACTIVE'
                    )
            GROUP BY d.NAME, i.instance_name,
                CASE
                    WHEN a.backup_count > 0 THEN 1
                    ELSE 0
                END
    )