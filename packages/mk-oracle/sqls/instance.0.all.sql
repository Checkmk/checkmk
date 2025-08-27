-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section instance: summary of the current Oracle database's runtime status, configuration, and role
SELECT UPPER(i.instance_name),                           -- Instance name in uppercase (e.g., ORCL1)
       i.VERSION,                                        -- Oracle database version (e.g., 19.0.0.0.0)
       i.STATUS,                                         -- Instance status: STARTED, MOUNTED, OPEN
       i.LOGINS,                                         -- Login status: ALLOWED, RESTRICTED, DISABLED
       i.ARCHIVER,                                       -- Archive log status: STARTED, STOPPED, FAILED
       ROUND((SYSDATE - i.startup_time) * 24 * 60 * 60), -- Uptime in seconds since instance started
       DBID,                                             -- Database Identifier (unique per DB)
       LOG_MODE,                                         -- Archive log mode: ARCHIVELOG or NOARCHIVELOG
       DATABASE_ROLE,                                    -- Database role: PRIMARY, PHYSICAL STANDBY, etc.
       FORCE_LOGGING,                                    -- Indicates if FORCE LOGGING is enabled (YES/NO)
       d.name,                                           -- Database name
       TO_CHAR(d.created, 'ddmmyyyyhh24mi'),             -- Database creation date/time in custom format
       i.host_name                                       -- Hostname of the server running the instance
FROM v$instance i,
     v$database d -- Cross join used for combining instance and DB metadata