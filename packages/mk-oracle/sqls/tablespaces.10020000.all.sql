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

/*
Section tablespaces: retrieves all tablespace file details for both:
- Permanent tablespaces (from dba_data_files)
- Temporary tablespaces (from dba_temp_files)

It reports file status, size, growth properties, free blocks, and tablespace type.
The query is filtered for PRIMARY databases only (ignores standby databases).
 */

-- === Section 1: Permanent Tablespaces (CDB Datafiles - all containers) ===
-- Returns permanent tablespaces for CDB$ROOT (as DATABASE) and all PDBs (as DATABASE.PDBNAME)
-- Excludes PDB$SEED (con_id = 2) as it's a template container
SELECT UPPER(DECODE(:IGNORE_DB_NAME, 0, c.db_name, i.instance_name)),
       dbf.file_name,                                     -- Full path of the datafile
       dbf.tablespace_name,                               -- Owning tablespace name
       dbf.fstatus,                                       -- File status (AVAILABLE, INVALID, etc.)
       dbf.autoextensible,                                -- Whether file can autoextend (YES/NO)
       dbf.blocks,                                        -- Current allocated blocks
       dbf.maxblocks,                                     -- Maximum possible blocks if autoextending
       dbf.user_blocks,                                   -- Blocks usable for user data
       dbf.increment_by,                                  -- Growth increment in blocks (if autoextend is enabled)
       dbf.online_status,                                 -- ONLINE / OFFLINE status of datafile
       dbf.block_size,                                    -- Block size of the tablespace
       DECODE(dbf.tstatus, 'READ ONLY', 'READONLY', dbf.tstatus), -- Tablespace mode
       dbf.free_blocks,                                   -- Available free blocks in this file
       dbf.contents,                                      -- Tablespace type (PERMANENT, UNDO, etc.)
       i.version                                          -- Database version from v$instance
FROM v$database d
         JOIN v$instance i ON 1 = 1
         JOIN (SELECT f.con_id,
                      f.file_name,
                      f.tablespace_name,
                      f.status               fstatus,
                      f.autoextensible,
                      f.blocks,
                      f.maxblocks,
                      f.user_blocks,
                      f.increment_by,
                      f.online_status,
                      t.block_size,
                      t.status               tstatus,
                      NVL(SUM(fs.blocks), 0) free_blocks,
                      t.contents
               FROM cdb_data_files f
                        JOIN cdb_tablespaces t ON f.tablespace_name = t.tablespace_name
                   AND f.con_id = t.con_id
                        LEFT OUTER JOIN cdb_free_space fs ON f.file_id = fs.file_id
                   AND f.con_id = fs.con_id
               GROUP BY f.con_id,
                        f.file_name,
                        f.tablespace_name,
                        f.status,
                        f.autoextensible,
                        f.blocks,
                        f.maxblocks,
                        f.user_blocks,
                        f.increment_by,
                        f.online_status,
                        t.block_size,
                        t.status,
                        t.contents
              ) dbf ON 1 = 1
         JOIN (SELECT vc.con_id,
                      DECODE(vc.con_id, 1, d.name, d.name || '.' || vc.name) db_name
               FROM v$containers vc
                        JOIN v$database d ON 1 = 1
               WHERE vc.con_id <> 2 -- Exclude PDB$SEED
              ) c ON dbf.con_id = c.con_id
WHERE d.database_role = 'PRIMARY'

UNION ALL

-- === Section 2: Temporary Tablespaces (CDB Tempfiles - all containers) ===
-- Returns temporary tablespaces for CDB$ROOT (as DATABASE) and all PDBs (as DATABASE.PDBNAME)
-- Excludes PDB$SEED (con_id = 2) as it's a template container
SELECT UPPER(DECODE(:IGNORE_DB_NAME, 0, c.db_name, i.instance_name)),
       dbf.file_name,                                     -- Tempfile path
       dbf.tablespace_name,                               -- Temp tablespace name
       dbf.fstatus,                                       -- Tempfile status
       dbf.autoextensible,                                -- Autoextend enabled or not
       dbf.blocks,                                        -- Allocated blocks
       dbf.maxblocks,                                     -- Maximum possible blocks
       dbf.user_blocks,                                   -- Blocks usable for data
       dbf.increment_by,                                  -- Autoextend increment
       dbf.online_status,                                 -- ONLINE (temp is always online)
       dbf.block_size,                                    -- Tablespace block size
       DECODE(dbf.tstatus, 'READ ONLY', 'READONLY', dbf.tstatus), -- Mode
       dbf.free_blocks,                                   -- Free space (allocated - used by temp segs)
       'TEMPORARY',                                       -- Force label TEMPORARY
       i.version                                          -- DB version from v$instance
FROM v$database d
         JOIN v$instance i ON 1 = 1
         JOIN (SELECT f.con_id,
                      f.file_name,
                      t.tablespace_name,
                      f.status                          fstatus,
                      f.autoextensible,
                      f.blocks,
                      f.maxblocks,
                      f.user_blocks,
                      f.increment_by,
                      'ONLINE'                          online_status,
                      t.block_size,
                      t.status                          tstatus,
                      f.blocks - NVL(SUM(tu.blocks), 0) free_blocks,
                      t.contents
               FROM cdb_tablespaces t
                        JOIN cdb_temp_files f ON t.tablespace_name = f.tablespace_name
                   AND t.con_id = f.con_id
                        LEFT OUTER JOIN gv$tempseg_usage tu ON f.con_id = tu.con_id
                   AND f.tablespace_name = tu.tablespace
                   AND f.RELATIVE_FNO = tu.SEGRFNO#
               WHERE t.contents = 'TEMPORARY'
               GROUP BY f.con_id,
                        f.file_name,
                        t.tablespace_name,
                        f.status,
                        f.autoextensible,
                        f.blocks,
                        f.maxblocks,
                        f.user_blocks,
                        f.increment_by,
                        t.block_size,
                        t.status,
                        t.contents
              ) dbf ON 1 = 1
         JOIN (SELECT vc.con_id,
                      d.name || '.' || vc.name db_name
               FROM v$containers vc
                        JOIN v$database d ON 1 = 1
               WHERE vc.con_id <> 2 -- Exclude PDB$SEED
              ) c ON dbf.con_id = c.con_id
WHERE d.database_role = 'PRIMARY'
