-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section longactivesessions: etrieves details of active foreground user sessions
-- that have been running for over 1 hour
SELECT UPPER(i.instance_name) AS instance_name, -- Instance name (uppercased)
       s.sid,                                   -- Session ID
       s.serial#,                               -- Session serial number (for uniqueness with SID)
       s.machine,                               -- Client machine name
       s.process,                               -- OS process ID of the client session
       s.osuser,                                -- Operating system user
       s.program,                               -- Application/program name
       s.last_call_et,                          -- Elapsed time (in seconds) since the session's last activity
       s.sql_id                                 -- SQL_ID of the currently executing SQL
FROM v$session s,
     v$instance i
WHERE s.status = 'ACTIVE'          -- Only active sessions (currently executing SQL)
  AND s.type != 'BACKGROUND'       -- Exclude Oracle background processes
  AND s.username IS NOT NULL       -- Only user sessions
  AND s.username NOT IN ('PUBLIC') -- Exclude system pseudo-users
  AND s.last_call_et > 60 * 60     -- Running for more than 1 hour (3600 seconds)
UNION ALL
-- Fallback: if no long-running sessions exist, return the instance name with nulls
SELECT UPPER(i.instance_name),
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL
FROM v$instance i