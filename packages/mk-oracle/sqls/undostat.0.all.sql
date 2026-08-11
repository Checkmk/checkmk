-- Copyright (C) 2025 Checkmk GmbH
--
-- Licensed under the Apache License, Version 2.0 (the "License")
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--    http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
--
-- SPDX-License-Identifier: Apache-2.0

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