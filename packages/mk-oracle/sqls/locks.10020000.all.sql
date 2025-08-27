-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section locks: retrieves blocking session information in an Oracle database
SELECT UPPER(i.instance_name) AS instance_name, -- Instance name
       b.sid,                                   -- Session ID of the blocked session
       b.serial#,                               -- Serial# of the blocked session
       b.machine,                               -- Client machine name of blocked session
       b.program,                               -- Program/application name of blocked session
       b.process,                               -- OS process ID of blocked session
       b.osuser,                                -- OS user of blocked session
       b.username,                              -- Oracle DB user of blocked session
       b.SECONDS_IN_WAIT,                       -- Seconds the session has been waiting
       b.BLOCKING_SESSION_STATUS,               -- Status of the blocking session (VALID, UNKNOWN, etc.)
       bs.inst_id,                              -- Instance ID of the blocking session (for RAC)
       bs.sid,                                  -- Session ID of the blocking session
       bs.serial#,                              -- Serial# of the blocking session
       bs.machine,                              -- Client machine name of blocking session
       bs.program,                              -- Program/application name of blocking session
       bs.process,                              -- OS process ID of blocking session
       bs.osuser,                               -- OS user of blocking session
       bs.username                              -- Oracle DB user of blocking session
FROM v$session b
         JOIN v$instance i
              ON 1 = 1
         JOIN gv$session bs
              ON bs.inst_id = b.BLOCKING_INSTANCE -- Match blocking session's instance (RAC support)
                  AND bs.sid = b.BLOCKING_SESSION -- Match blocking session's SID
WHERE b.BLOCKING_SESSION IS NOT NULL -- Only sessions that are blocked
UNION ALL
-- If no blocking sessions exist, return just the instance name with nulls
SELECT UPPER(i.instance_name),
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL
FROM v$instance i