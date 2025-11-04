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
