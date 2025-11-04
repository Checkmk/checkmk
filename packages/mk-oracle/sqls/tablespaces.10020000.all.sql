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
Section tablespaces: retrieves details about all datafiles and tempfiles in the database, including:
- Tablespace names and file paths
- File status and autoextensibility
- Space usage: total blocks, free blocks, max size, growth increment
- Online status and read/write mode (READ WRITE vs READ ONLY)
- Tablespace type (PERMANENT vs TEMPORARY)
- Database name, version, and role (filtered for PRIMARY database
*/

-- === Section 1: Permanent Tablespaces (Datafiles) ===
SELECT UPPER(d.NAME),                                     -- Database name (uppercase)
       file_name,                                         -- Full OS path of datafile
       tablespace_name,                                   -- Name of owning tablespace
       fstatus,                                           -- Datafile status (e.g., AVAILABLE, INVALID)
       autoextensible,                                    -- If file autoextends (YES/NO)
       blocks,                                            -- Current allocated blocks in file
       maxblocks,                                         -- Max possible blocks if autoextensible
       user_blocks,                                       -- Blocks usable for user segments
       increment_by,                                      -- Growth increment (in blocks) if autoextend enabled
       online_status,                                     -- ONLINE / OFFLINE status of the file
       block_size,                                        -- Tablespace block size
       DECODE(tstatus, 'READ ONLY', 'READONLY', tstatus), -- Tablespace status (READONLY/READ WRITE)
       free_blocks,                                       -- Free space in blocks
       contents,                                          -- Tablespace type (PERMANENT, UNDO, etc.)
       iversion                                           -- Instance version (from v$instance)
FROM v$database d,
     v$instance i,
     (SELECT f.file_name,
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
             NVL(SUM(fs.blocks), 0) free_blocks, -- Free space aggregated from dba_free_space
             t.contents,
             (SELECT version
              FROM v$instance
             )                      iversion     -- Current DB version
      FROM dba_data_files f
               JOIN dba_tablespaces t ON f.tablespace_name = t.tablespace_name
               LEFT JOIN dba_free_space fs ON f.file_id = fs.file_id
      GROUP BY f.file_name,
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
     )
WHERE d.database_role = 'PRIMARY' -- Only report for PRIMARY role database

UNION ALL

-- === Section 2: Temporary Tablespaces (Tempfiles) ===
SELECT UPPER(dbf.name),                                   -- Database name
       dbf.file_name,                                     -- Tempfile OS path
       dbf.tablespace_name,                               -- Temp tablespace name
       dbf.fstatus,                                       -- Tempfile status
       dbf.autoextensible,                                -- Autoextend flag
       dbf.blocks,                                        -- Allocated blocks
       dbf.maxblocks,                                     -- Maximum blocks
       dbf.user_blocks,                                   -- User-usable blocks
       dbf.increment_by,                                  -- Growth increment
       dbf.online_status,                                 -- Always ONLINE for temp
       dbf.block_size,                                    -- Block size
       DECODE(tstatus, 'READ ONLY', 'READONLY', tstatus), -- Tablespace mode
       dbf.free_blocks,                                   -- Free blocks (allocated - used by temp segments)
       'TEMPORARY',                                       -- Marked explicitly as TEMPORARY
       i.version                                          -- Instance version
FROM v$database d
         JOIN v$instance i ON 1 = 1
         JOIN (SELECT vp.name,
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
                      f.blocks - NVL(SUM(tu.blocks), 0) free_blocks, -- Used blocks deducted
                      t.contents
               FROM dba_tablespaces t
                        JOIN (SELECT 0, name
                              FROM v$database
                             ) vp ON 1 = 1
                        LEFT JOIN dba_temp_files f ON t.tablespace_name = f.tablespace_name
                        LEFT JOIN gv$tempseg_usage tu
                                  ON f.tablespace_name = tu.tablespace
                                      AND f.RELATIVE_FNO = tu.SEGRFNO#
               WHERE t.contents = 'TEMPORARY' -- Only temp tablespaces
               GROUP BY vp.name,
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
