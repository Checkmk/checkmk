-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section undostat: retrieves latest undo tablespace stats while being CDB/PDB aware
SELECT DECODE(
               vp.con_id, NULL, UPPER(i.INSTANCE_NAME), UPPER(i.INSTANCE_NAME || '.' || vp.name)
       ) AS instance_pdb_name, -- If no PDB, just use instance name
       ACTIVEBLKS,             -- Active undo blocks in use
       MAXCONCURRENCY,         -- Peak concurrent transactions
       TUNED_UNDORETENTION,    -- Auto-tuned undo retention (in seconds)
       maxquerylen,            -- Longest-running query observed in this interval
       NOSPACEERRCNT           -- Undo allocation errors (out of space issues)
FROM v$instance i -- Instance information
-- Get most recent undo statistics snapshot
         JOIN (SELECT *
               FROM v$undostat
               WHERE TUNED_UNDORETENTION > 0 -- Only keep valid records
               ORDER BY end_time DESC
                   FETCH NEXT 1 ROWS ONLY -- Get only the latest snapshot
              ) u ON 1 = 1
         LEFT OUTER JOIN v$pdbs vp -- Join to PDBs for multitenant environment
                         ON vp.con_id = u.con_id