-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section sessions: retrieves session usage statistics per container (CDB / PDB)

--- === Section 1: retrieves session usage statistics for PDB only ===
SELECT UPPER(vp.name)  AS instance_name,   -- PDB name (uppercased)
       LTRIM(COUNT(1)) AS current_sessions -- Number of currently active sessions
FROM (
         -- Step 1: Build container list
         SELECT vp.con_id,
                i.instance_name || '.' || vp.name name -- Instance + PDB name
         FROM v$containers vp
                  JOIN v$instance i ON 1 = 1
                  JOIN v$database d ON 1 = 1
         WHERE d.cdb = 'YES' -- Only if running in multitenant mode
           AND vp.con_id <> 2 -- Exclude seed PDB (PDB$SEED)
     ) vp
         -- Step 2: Join with resource limits
         JOIN v$resource_limit rl
              ON RESOURCE_NAME = 'sessions' -- Only look at session resource limit
    -- Step 3: Count active sessions per container
         LEFT OUTER JOIN v$session vs
                         ON vp.con_id = vs.con_id -- Map sessions to each container
GROUP BY vp.name, vp.con_id, rl.LIMIT_VALUE, rl.MAX_UTILIZATION;

-- === Section 2: retrieves session usage statistics for CDB (root container) only ===
SELECT UPPER(vp.instance_name)       AS instance_name,    -- CDB / PDB name (uppercased)
       LTRIM(COUNT(1))               AS current_sessions, -- Number of currently active sessions
       LTRIM(RTRIM(LIMIT_VALUE))     AS limit_sessions,   -- Configured session limit
       LTRIM(RTRIM(MAX_UTILIZATION)) AS MAX_UTILIZATION   -- Peak session usage so far
FROM (
         -- Include root container (CDB) as con_id = 0
         SELECT 0, instance_name
         FROM v$instance i
     ) vp
         -- Step 2: Join with resource limits
         JOIN v$resource_limit rl
              ON RESOURCE_NAME = 'sessions' -- Only look at session resource limit
GROUP BY vp.instance_name, rl.LIMIT_VALUE, rl.MAX_UTILIZATION
