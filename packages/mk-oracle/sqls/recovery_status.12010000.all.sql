-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section recovery_status: retrieves datafile checkpoint and backup status
-- in both CDB (multitenant) and non-CDB databases
SELECT UPPER(
           DECODE(NVL(:IGNORE_DB_NAME, 0),
                  0,
                  DECODE(vp.con_id, NULL, d.NAME, d.NAME || '.' || vp.name), -- Show PDB name if available
                  i.instance_name) -- Otherwise show instance name
       ),
       d.DB_UNIQUE_NAME,                                     -- Unique DB name (useful in Data Guard / RAC)
       d.DATABASE_ROLE,                                      -- PRIMARY, STANDBY, etc.
       d.open_mode,                                          -- OPEN, MOUNTED, READ ONLY
       dh.file#,                                             -- Datafile number
       round((dh.CHECKPOINT_TIME - to_date('01.01.1970', 'dd.mm.yyyy')) * 24 * 60 *
             60),                                            -- Checkpoint time in epoch seconds
       round((sysdate - dh.CHECKPOINT_TIME) * 24 * 60 * 60), -- Time since last checkpoint (seconds)
       dh.STATUS,                                            -- Datafile status (ONLINE, OFFLINE, etc.)
       dh.RECOVER,                                           -- Indicates if recovery is required
       dh.FUZZY,                                             -- "YES" if checkpoint is not complete
       dh.CHECKPOINT_CHANGE#,                                -- Checkpoint SCN
       NVL(vb.STATUS, 'unknown'),                            -- Backup status from v$backup (e.g., ACTIVE)
       NVL2(vb.TIME, -- If backup time exists, calculate seconds since backup started
            round((sysdate - vb.TIME) * 24 * 60 * 60),
            0)
FROM v$datafile_header dh
         JOIN v$database d ON 1 = 1
         JOIN v$instance i ON 1 = 1
         LEFT OUTER JOIN v$backup vb
                         ON vb.file# = dh.file# -- Match datafile with backup info
         LEFT OUTER JOIN V$PDBS vp
                         ON dh.con_id = vp.con_id -- Match datafile to specific PDB
ORDER BY dh.file#