-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

/*
Section tablespaces: retrieves all tablespace file details for both:
- Permanent tablespaces (from dba_data_files)
- Temporary tablespaces (from dba_temp_files)

It reports file status, size, growth properties, free blocks, and tablespace type.
The query is filtered for PRIMARY databases only (ignores standby databases).
 */

-- === Section 1: Permanent Tablespaces (Datafiles) ===
SELECT UPPER(d.NAME),                                     -- Database name (uppercase)
       file_name,                                         -- Full path of the datafile
       tablespace_name,                                   -- Owning tablespace name
       fstatus,                                           -- File status (AVAILABLE, INVALID, etc.)
       autoextensible,                                    -- Whether file can autoextend (YES/NO)
       blocks,                                            -- Current allocated blocks
       maxblocks,                                         -- Maximum possible blocks if autoextending
       user_blocks,                                       -- Blocks usable for user data
       increment_by,                                      -- Growth increment in blocks (if autoextend is enabled)
       online_status,                                     -- ONLINE / OFFLINE status of datafile
       block_size,                                        -- Block size of the tablespace
       DECODE(tstatus, 'READ ONLY', 'READONLY', tstatus), -- Tablespace mode
       free_blocks,                                       -- Available free blocks in this file
       contents,                                          -- Tablespace type (PERMANENT, UNDO, etc.)
       iversion                                           -- Database version from v$instance
FROM v$database d,
     v$instance i, -- Instance info
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
             NVL(SUM(fs.blocks), 0) free_blocks, -- Free blocks from dba_free_space
             t.contents,
             (SELECT version
              FROM v$instance
             )                      iversion     -- Instance version
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
WHERE d.database_role = 'PRIMARY' -- Report only for PRIMARY DB

UNION ALL

-- === Section 2: Temporary Tablespaces (Tempfiles) ===
SELECT UPPER(dbf.name),                                   -- Database name
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
       DECODE(tstatus, 'READ ONLY', 'READONLY', tstatus), -- Mode
       dbf.free_blocks,                                   -- Free space (allocated - used by temp segs)
       'TEMPORARY',                                       -- Force label TEMPORARY
       i.version                                          -- DB version from v$instance
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
                      'ONLINE'                          online_status, -- Temp always ONLINE
                      t.block_size,
                      t.status                          tstatus,
                      f.blocks - NVL(SUM(tu.blocks), 0) free_blocks,   -- Used deducted
                      t.contents
               FROM dba_tablespaces t
                        JOIN (SELECT 0, name
                              FROM v$database
                             ) vp ON 1 = 1
                        LEFT JOIN dba_temp_files f ON t.tablespace_name = f.tablespace_name
                        LEFT JOIN gv$tempseg_usage tu
                                  ON f.tablespace_name = tu.tablespace
                                      AND f.RELATIVE_FNO = tu.SEGRFNO#
               WHERE t.contents = 'TEMPORARY' -- Only TEMPORARY tablespaces
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
