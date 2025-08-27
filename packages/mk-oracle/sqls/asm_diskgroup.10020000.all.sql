-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section asm_diskgroup: retrieves key storage and status metrics for all ASM diskgroups in the Oracle database,
-- it provides details about space usage, redundancy type, disk status, and configuration parameters.
SELECT STATE,                   -- Current state of the diskgroup (e.g., MOUNTED, DISMOUNTED, CONNECTED)
       TYPE,                    -- Redundancy level of the diskgroup (EXTERNAL, NORMAL, HIGH)
       'N',
       sector_size,             -- Physical sector size (in bytes) of the underlying ASM disks.
       block_size,              -- Block size used within the ASM diskgroup
       allocation_unit_size,    -- Allocation unit size in bytes (how ASM allocates storage)
       total_mb,                -- Total capacity of the diskgroup in megabytes
       free_mb,                 -- Currently available free space in megabytes
       required_mirror_free_mb, -- Amount of space required to maintain redundancy if a failure occurs
       usable_file_mb,          -- Space available for user files after considering redundancy overhead
       offline_disks,           -- Number of disks currently offline in the diskgroup
       'N',
       name,                    -- Name of the ASM diskgroup
       '/'
FROM v$asm_diskgroup -- Dynamic performance view for ASM diskgroup metadata and metrics