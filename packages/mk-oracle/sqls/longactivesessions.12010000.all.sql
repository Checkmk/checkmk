-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section longactivesessions: retrieves long-running active user sessions (> 1 hour)
-- across all containers (CDB root + PDBs).
SELECT UPPER(vp.name) AS pdb_instance_name, -- Fully qualified instance/container name (e.g., INSTANCE.PDB)
       s.sid,                               -- Session ID
       s.serial#,                           -- Serial number (for unique session identification)
       s.machine,                           -- Client machine name
       s.process,                           -- Client OS process ID
       s.osuser,                            -- Client operating system user
       s.program,                           -- Program/application name
       s.last_call_et,                      -- Elapsed time (in seconds) since the SQL started
       s.sql_id                             -- SQL_ID of the executing statement
FROM v$session s
         JOIN (
    -- Build list of instances and containers (CDB + PDBs)
    SELECT vp.con_id,
           i.instance_name || '.' || vp.name AS name -- Qualify instance with PDB name
    FROM v$containers vp
             JOIN v$instance i ON 1 = 1
             JOIN v$database d ON 1 = 1
    WHERE d.cdb = 'YES'  -- Only applies if database is a Container Database
      AND vp.con_id <> 2 -- Exclude PDB$SEED (template PDB)
    UNION ALL
    SELECT 0, instance_name -- Non-CDB fallback
    FROM v$instance
              ) vp
              ON 1 = 1 -- Cartesian join, allows tagging sessions with instance/container
WHERE s.status = 'ACTIVE'          -- Only active sessions
  AND s.type != 'BACKGROUND'       -- Exclude Oracle background processes
  AND s.username IS NOT NULL       -- Only user sessions
  AND s.username NOT IN ('PUBLIC') -- Exclude pseudo-users
  AND s.last_call_et > 60 * 60     -- Active for more than 1 hour
UNION ALL
-- Fallback: return container name with nulls if no long-running sessions exist
SELECT UPPER(i.instance_name || '.' || vp.name),
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
-- Fallback: handle non-CDB environments
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