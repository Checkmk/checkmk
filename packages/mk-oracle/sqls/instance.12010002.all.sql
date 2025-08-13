-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section instance
-- ATTENTION: must be patched with the version column ${version_column} -> version_full for >= 18.0.0.0 otherwise version
SELECT UPPER(instance_name)
           || '|' || VERSION
           || '|' || STATUS
           || '|' || LOGINS
           || '|' || ARCHIVER
           || '|' || ROUND((SYSDATE - STARTUP_TIME) * 24 * 60 * 60)
           || '|' || DBID
           || '|' || LOG_MODE
           || '|' || DATABASE_ROLE
           || '|' || FORCE_LOGGING
           || '|' || NAME
           || '|' || TO_CHAR(CREATED, 'ddmmyyyyhh24mi')
           || '|' || UPPER(VALUE)
           || '|' || CON_ID
           || '|' || PNAME
           || '|' || PDBID
           || '|' || POPEN_MODE
           || '|' || PRESTRICTED
           || '|' || PTOTAL_TIME
           || '|' || PRECOVERY_STATUS
           || '|' || ROUND(NVL(POPEN_TIME, -1))
           || '|' || PBLOCK_SIZE
           || '|' || HOST_NAME
    FROM (
         SELECT i.instance_name,
                i.host_name,
                i.${version_column} VERSION, -- either version or version_full
                i.STATUS,
                i.LOGINS,
                i.ARCHIVER,
                i.STARTUP_TIME,
                d.DBID,
                d.LOG_MODE,
                d.DATABASE_ROLE,
                d.FORCE_LOGGING,
                d.NAME,
                d.CREATED,
                p.VALUE,
                vp.CON_ID,
                vp.NAME PNAME,
                vp.DBID PDBID,
                vp.OPEN_MODE POPEN_MODE,
                vp.RESTRICTED PRESTRICTED,
                vp.TOTAL_SIZE PTOTAL_TIME,
                vp.BLOCK_SIZE PBLOCK_SIZE,
                vp.RECOVERY_STATUS PRECOVERY_STATUS,
                (CAST(SYSTIMESTAMP AS DATE) - CAST(OPEN_TIME AS DATE)) * 24 * 60 * 60 POPEN_TIME
            FROM v$instance i
            JOIN v$database d
                ON 1 = 1
            JOIN v$parameter p
                ON 1 = 1
            JOIN v$pdbs vp
                ON 1 = 1
            WHERE p.NAME = 'enable_pluggable_database'
         UNION ALL
         SELECT i.instance_name,
                i.host_name,
                i.${version_column} VERSION, -- either version or version_full
                i.STATUS,
                i.LOGINS,
                i.ARCHIVER,
                i.STARTUP_TIME,
                d.DBID,
                d.LOG_MODE,
                d.DATABASE_ROLE,
                d.FORCE_LOGGING,
                d.NAME, d.CREATED, p.VALUE, 0 CON_ID, NULL PNAME,
                0 PDBID,
                NULL POPEN_MODE,
                NULL PRESTRICTED,
                NULL PTOTAL_TIME,
                0 PBLOCK_SIZE,
                NULL PRECOVERY_STATUS,
                NULL POPEN_TIME
            FROM v$instance i
            JOIN v$database d
                ON 1 = 1
            JOIN v$parameter p
                ON 1 = 1
            WHERE p.NAME = 'enable_pluggable_database'
            ORDER BY CON_ID
     )