-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section instance, asm version: Retrieves metadata about the currently running Oracle database instance
-- ATTENTION: must be patched with the version column ${version_column} -> version_full for >= 18.0.0.0 otherwise version
SELECT DISTINCT UPPER(c.instance_name),                           -- Instance name in uppercase (e.g., 'ORCL1')
                i.${version_column},                              -- Oracle version info (e.g., VERSION or VERSION_FULL)
                i.STATUS,                                         -- Current status of the instance (e.g., OPEN, MOUNT, STARTED)
                i.LOGINS,                                         -- Login status: ALLOWED, RESTRICTED, or DISABLED
                i.ARCHIVER,                                       -- Archive log mode: STARTED, STOPPED, FAILED
                ROUND((SYSDATE - i.startup_time) * 24 * 60 * 60), -- Uptime in seconds since instance startup
                '0',
                'NO',
                'ASM',
                'NO',
                c.instance_name,                                  -- Original (unmodified) instance name
                i.host_name                                       -- Host machine on which the instance is running
FROM gv$asm_client c
         JOIN gv$instance i ON c.inst_id = i.inst_id
         JOIN gv$database d ON c.db_name = d.name
