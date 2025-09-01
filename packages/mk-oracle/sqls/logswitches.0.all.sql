-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section logswitches: retrieves the number of redo log switches (log file changes) in the last one hour
SELECT UPPER(i.instance_name) AS instance_name, -- Current Oracle instance name (uppercased)
       logswitches                              -- Number of redo log switches in the last hour
FROM v$instance i,
     (SELECT COUNT(1) logswitches -- Count how many log switches occurred
      FROM v$loghist h, -- Historical log switch events
           v$instance i
      WHERE h.first_time > SYSDATE - 1 / 24 -- Only consider log switches in the last 1 hour
        AND h.thread# = i.instance_number -- Match redo thread to the current instance (RAC support)
     )
