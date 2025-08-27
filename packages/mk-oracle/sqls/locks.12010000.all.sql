-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms AND
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section locks: retrieves blocking session details across all PDBs in a multitenant Oracle database
SELECT UPPER(vp.name) AS pdb_or_instance, -- Instance + PDB name (or instance name for non-CDB)
       b.sid,                             -- SID of blocked session
       b.serial#,                         -- Serial# of blocked session
       b.machine,                         -- Client machine of blocked session
       b.program,                         -- Program/application of blocked session
       b.process,                         -- OS process ID of blocked session
       b.osuser,                          -- OS user of blocked session
       b.username,                        -- Oracle user of blocked session
       b.SECONDS_IN_WAIT,                 -- How long session has been waiting (in seconds)
       b.BLOCKING_SESSION_STATUS,         -- Status of blocking session (VALID, UNKNOWN, etc.)
       bs.inst_id,                        -- Instance ID of blocking session (RAC support)
       bs.sid,                            -- SID of blocking session
       bs.serial#,                        -- Serial# of blocking session
       bs.machine,                        -- Client machine of blocking session
       bs.program,                        -- Program/application of blocking session
       bs.process,                        -- OS process ID of blocking session
       bs.osuser,                         -- OS user of blocking session
       bs.username                        -- Oracle user of blocking session
FROM v$session b
         JOIN gv$session bs
              ON bs.inst_id = b.BLOCKING_INSTANCE -- Match blocking session's instance
                  AND bs.sid = b.BLOCKING_SESSION -- Match blocking session's SID
                  AND bs.con_id = b.con_id -- Match same container (PDB)
         JOIN (
    -- Map con_id to instance + PDB name
    SELECT vp.con_id,
           i.instance_name || '.' || vp.name AS name
    FROM v$containers vp
             JOIN v$instance i ON 1 = 1
             JOIN v$database d ON 1 = 1
    WHERE d.cdb = 'YES'
      AND vp.con_id <> 2 -- Exclude seed PDB
    UNION ALL
    -- Non-CDB fallback
    SELECT 0, instance_name
    FROM v$instance
              ) vp
              ON b.con_id = vp.con_id
WHERE b.BLOCKING_SESSION IS NOT NULL -- Only show blocked sessions
UNION ALL
-- Ensure a row is returned even if no blocking sessions exist (per PDB)
SELECT UPPER(i.instance_name || '.' || vp.name),
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
FROM v$containers vp
         JOIN v$instance i ON 1 = 1
         JOIN v$database d ON 1 = 1
WHERE d.cdb = 'YES'
  AND vp.con_id <> 2
UNION ALL
-- Fallback row for non-CDB database
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