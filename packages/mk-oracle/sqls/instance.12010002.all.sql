-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section instance
-- ATTENTION: must be patched with the version column ${version_column} -> version_full for >= 18.0.0.0 otherwise version
SELECT UPPER(instance_name),                           -- Oracle instance name (uppercase)
       VERSION,                                        -- Oracle version (e.g., 19.12.0.0.0)
       STATUS,                                         -- Instance status (STARTED, MOUNTED, OPEN)
       LOGINS,                                         -- Whether logins are allowed
       ARCHIVER,                                       -- Archive log status (STARTED, STOPPED, FAILED)
       ROUND((SYSDATE - STARTUP_TIME) * 24 * 60 * 60), -- Uptime in seconds
       DBID,                                           -- Unique identifier for the database
       LOG_MODE,                                       -- Archive log mode (ARCHIVELOG/NOARCHIVELOG)
       DATABASE_ROLE,                                  -- Role: PRIMARY or STANDBY
       FORCE_LOGGING,                                  -- Whether FORCE LOGGING is enabled
       NAME,                                           -- Database name
       TO_CHAR(CREATED, 'ddmmyyyyhh24mi'),             -- Database creation timestamp
       UPPER(VALUE),                                   -- Value of 'enable_pluggable_database' parameter (usually TRUE)
       CON_ID,                                         -- Container ID (0 for CDB root, >0 for PDBs)
       PNAME,                                          -- Pluggable database name
       PDBID,                                          -- PDB ID
       POPEN_MODE,                                     -- PDB open mode: READ WRITE, MOUNTED, etc.
       PRESTRICTED,                                    -- Whether PDB is in RESTRICTED mode
       TOTAL_SIZE,                                     -- Size of the PDB
       PRECOVERY_STATUS,                               -- Recovery status of the PDB (e.g., NOT RECOVERED)
       ROUND(NVL(POPEN_TIME, -1)),                     -- Seconds since the PDB was opened (-1 if null)
       PBLOCK_SIZE,                                    -- PDB block size
       HOST_NAME                                       -- Host where the instance is running
FROM (
         -- === First part: Info for PDBs in a multitenant container ===
         SELECT i.instance_name,
                i.host_name,
                i.${version_column}                                            VERSION, -- Bind variable: version or version_full
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
                p.VALUE,                                                                -- Value of 'enable_pluggable_database' param
                vp.CON_ID,
                vp.NAME                                                        PNAME,   -- PDB name
                vp.DBID                                                        PDBID,   -- PDB ID
                vp.OPEN_MODE                                                   POPEN_MODE,
                vp.RESTRICTED                                                  PRESTRICTED,
                vp.TOTAL_SIZE                                                  TOTAL_SIZE,
                vp.BLOCK_SIZE                                                  PBLOCK_SIZE,
                vp.RECOVERY_STATUS                                             PRECOVERY_STATUS,
                (CAST(SYSTIMESTAMP AS DATE) - CAST(OPEN_TIME AS DATE)) * 86400 POPEN_TIME
         FROM v$instance i
                  JOIN v$database d ON 1 = 1
                  JOIN v$parameter p ON 1 = 1
                  JOIN v$pdbs vp ON 1 = 1
         WHERE p.NAME = 'enable_pluggable_database'

         UNION ALL

         -- === Second part: fallback for non-multitenant (CDB only) ===
         SELECT i.instance_name,
                i.host_name,
                i.${version_column} VERSION,
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
                0                   CON_ID, -- Defaults for non-PDB environments
                NULL                PNAME,
                0                   PDBID,
                NULL                POPEN_MODE,
                NULL                PRESTRICTED,
                NULL                PTOTAL_TIME,
                0                   PBLOCK_SIZE,
                NULL                PRECOVERY_STATUS,
                NULL                POPEN_TIME
         FROM v$instance i
                  JOIN v$database d ON 1 = 1
                  JOIN v$parameter p ON 1 = 1
         WHERE p.NAME = 'enable_pluggable_database'

         ORDER BY CON_ID
     )