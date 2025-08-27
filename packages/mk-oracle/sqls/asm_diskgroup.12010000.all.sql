-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section asm_diskgroup: retrieves detailed storage and redundancy metrics for each
-- ASM diskgroup and its associated failgroups
SELECT g.state,                     -- Diskgroup state: MOUNTED, DISMOUNTED, CONNECTED
       g.type,                      -- Redundancy type: EXTERNAL, NORMAL, HIGH
       g.name,                      -- Name of the ASM diskgroup
       g.BLOCK_SIZE,                -- Block size used by the ASM diskgroup
       g.ALLOCATION_UNIT_SIZE,      -- Allocation unit size in bytes
       g.REQUIRED_MIRROR_FREE_MB,   -- Space reserved to maintain redundancy on disk failure
       SUM(d.total_mb),             -- Total size of all disks in the failgroup (in MB)
       SUM(d.free_mb),              -- Free space available across all disks in the failgroup
       d.failgroup,                 -- The failgroup the disk belongs to
       MAX(d.VOTING_FILE),          -- Indicates if any disk in the failgroup holds a voting file ('Y' or 'N')
       d.FAILGROUP_TYPE,            -- Type of failgroup (e.g., REGULAR, QUORUM)
       g.offline_disks,             -- Number of disks currently offline in the diskgroup
       MIN(DECODE(d.REPAIR_TIMER,
                  0, 8640000,
                  d.REPAIR_TIMER)), -- Lowest repair timer value (0 replaced with default 8640000)
       COUNT(*)                     -- Number of disks in the group/failgroup combination
FROM v$asm_diskgroup g
         LEFT OUTER JOIN
     v$asm_disk d
     ON d.group_number = g.group_number -- Join diskgroups to their associated disks
         AND d.group_number <> 0 -- Ignore unassociated disks
GROUP BY g.name,
         g.state,
         g.type,
         d.failgroup,
         d.VOTING_FILE,
         g.BLOCK_SIZE,
         g.ALLOCATION_UNIT_SIZE,
         g.REQUIRED_MIRROR_FREE_MB,
         g.offline_disks,
         d.FAILGROUP_TYPE,
         d.REPAIR_TIMER
ORDER BY g.name,
         d.failgroup
