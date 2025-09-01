-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section recovery_status: retrieves datafile checkpoint information
SELECT UPPER(
               DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)
       )        AS instance_name,         -- Database name or Instance name (uppercase), depends on :IGNORE_DB_NAME
       d.DB_UNIQUE_NAME,                  -- Unique name of the database (for Data Guard / RAC environments)
       d.DATABASE_ROLE,                   -- Database role (PRIMARY / STANDBY)
       d.open_mode,                       -- Database open mode (READ WRITE / READ ONLY / MOUNTED)
       dh.file# AS file_id,               -- Datafile number
       ROUND(
               (dh.CHECKPOINT_TIME - TO_DATE('01.01.1970', 'dd.mm.yyyy')) * 24 * 60 * 60
       )        AS checkpoint_epoch,      -- Checkpoint time converted to Unix epoch (seconds since 1970-01-01)
       ROUND(
               (SYSDATE - dh.CHECKPOINT_TIME) * 24 * 60 * 60
       )        AS secs_since_checkpoint, -- Seconds since last checkpoint
       dh.STATUS,                         -- Datafile status (ONLINE / OFFLINE / SYSTEM)
       dh.RECOVER,                        -- Whether recovery is needed (YES/NO)
       dh.FUZZY,                          -- Indicates whether the datafile contains fuzzy (not fully written) data
       dh.CHECKPOINT_CHANGE#              -- SCN at the last checkpoint
FROM v$datafile_header dh,
     v$database d,
     v$instance i
ORDER BY dh.file# -- Order results by datafile number