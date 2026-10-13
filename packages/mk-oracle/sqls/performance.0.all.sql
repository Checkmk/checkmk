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
Section performance: retrieves a health snapshot of an Oracle database, supporting both:
- Non-CDB (traditional single-instance databases)
- CDB/PDB (multitenant databases with container architecture).

Collects metrics from:
- Time model (DB time, DB CPU) – per instance or per container.
- System wait classes – categorizes non-idle waits (e.g., User I/O, Concurrency, Commit).
- Buffer pool statistics – logical/physical I/O, waits.
- SGA memory information – breakdown of shared memory structures.
- Library cache efficiency – SQL/PLSQL cache lookup and execution performance.
- PGA statistics – memory usage of the container the query runs in.
*/

-- TODO(sk): the sections below carry a
-- SYS_CONTEXT('USERENV','CON_ID') IN ('0', '1') guard because this file is
-- executed once per container, while only the PGA statement needs that. Move
-- the PGA statement into its own section and drop the guards.
-- === Section 1: System time model (CPU & DB time) ===
SELECT UPPER(
               DECODE(cdb, 'NO', instance_name, instance_name || '.' || con_name)
       )                AS instance_name,
       'sys_time_model' AS metric_type, -- Label to identify metric group
       STAT_NAME,                       -- 'DB time' or 'DB CPU'
       ROUND(value / 1000000)          -- Convert microseconds to seconds
FROM (
         -- Case 1: Multitenant (CDB = YES)
         SELECT d.cdb, i.instance_name, s.stat_name, s.value, vd.name con_name
         FROM v$instance i
                  JOIN v$con_sys_time_model s
                       ON s.stat_name IN ('DB time', 'DB CPU') -- Only DB time & CPU
                  JOIN v$containers vd
                       ON vd.con_id = s.con_id -- Per-PDB stats
                  JOIN v$database d ON d.cdb = 'YES'
         WHERE vd.con_id <> 2 -- Exclude seed PDB
         UNION ALL
         -- Case 2: Non-CDB (classic database)
         SELECT d.cdb, i.instance_name, s.stat_name, s.value, NULL
         FROM v$instance i
                  JOIN v$sys_time_model s
                       ON s.stat_name IN ('DB time', 'DB CPU')
                  JOIN v$database d ON d.cdb = 'NO'
     )
WHERE SYS_CONTEXT('USERENV','CON_ID') IN ('0', '1')
ORDER BY stat_name;
-- === Section 2: Wait class statistics ===
SELECT UPPER(DECODE(cdb, 'NO', INSTANCE_NAME, INSTANCE_NAME || '.' || con_name)),
       'sys_wait_class',                        -- Label for wait events
       WAIT_CLASS,                              -- e.g., "Concurrency", "Commit", etc.
       ROUND(total_waits),
       CAST(ROUND(time_waited) AS VARCHAR(64)), -- Time waited in centiseconds
       ROUND(total_waits_fg),                   -- Foreground (user session) waits
       ROUND(time_waited_fg)                    -- Foreground wait time
FROM (
         -- Case 1: Multitenant
         SELECT i.instance_name,
                vd.con_id,
                s.WAIT_CLASS,
                s.total_waits,
                s.time_waited,
                s.total_waits_fg,
                s.time_waited_fg,
                vd.name con_name,
                d.cdb
         FROM v$instance i
                  JOIN v$database d ON d.cdb = 'YES'
                  JOIN v$containers vd ON 1 = 1
                  JOIN v$con_system_wait_class s ON vd.con_id = s.con_id
         WHERE s.WAIT_CLASS <> 'Idle' -- Exclude idle waits
         UNION ALL
         -- Case 2: Non-CDB
         SELECT i.instance_name,
                0,
                s.WAIT_CLASS,
                s.total_waits,
                s.time_waited,
                s.total_waits_fg,
                s.time_waited_fg,
                NULL,
                d.cdb
         FROM v$instance i
                  JOIN v$database d ON d.cdb = 'NO'
                  JOIN v$system_wait_class s ON s.WAIT_CLASS <> 'Idle'
     )
WHERE SYS_CONTEXT('USERENV','CON_ID') IN ('0', '1')
ORDER BY con_name, wait_class;
-- === Section 3: Buffer pool statistics ===
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.CDB$ROOT')),
       'buffer_pool_statistics',
       b.name,             -- Buffer pool name (DEFAULT, KEEP, RECYCLE)
       b.db_block_gets,    -- # of block gets
       CAST(b.db_block_change AS VARCHAR(64)),
       b.consistent_gets,  -- Consistent reads
       b.physical_reads,   -- Physical reads
       b.physical_writes,  -- Physical writes
       b.FREE_BUFFER_WAIT, -- Waits due to free buffer shortage
       b.BUFFER_BUSY_WAIT  -- Contention for buffers
FROM v$instance i
         JOIN v$buffer_pool_statistics b ON b.con_id = 0
         JOIN v$database d ON 1 = 1
WHERE SYS_CONTEXT('USERENV','CON_ID') IN ('0', '1');
-- === Section 4: SGA information ===
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.CDB$ROOT')),
       'SGA_info',
       s.name,  -- SGA component (Buffer Cache, Shared Pool, etc.)
       s.bytes  -- Size in bytes
FROM v$instance i
         JOIN v$sgainfo s ON s.con_id = 0
         JOIN v$database d ON 1 = 1
WHERE SYS_CONTEXT('USERENV','CON_ID') IN ('0', '1');
-- === Section 5: Library cache stats ===
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.CDB$ROOT')),
       'librarycache',
       b.namespace,                    -- Cache namespace (SQL AREA, TABLE/PROCEDURE, etc.)
       b.gets,                         -- Lookups
       CAST(b.gethits AS VARCHAR(64)), -- Lookup hits
       b.pins,                         -- Executions
       b.pinhits,                      -- Execution hits
       b.reloads,                      -- Reloads required
       b.invalidations                 -- Invalidations
FROM v$instance i
         JOIN v$librarycache b ON b.con_id = 0
         JOIN v$database d ON 1 = 1
WHERE SYS_CONTEXT('USERENV','CON_ID') IN ('0', '1');
-- === Section 6: PGA statistics ===
-- v$pgastat has no v$con_ twin: it only yields a container's rows when the
-- query runs inside that container. The section is therefore executed once per
-- container (root plus every matching PDB) and this statement reports whichever
-- one it currently runs in - the same thing the legacy plugin achieved with
-- dbms_sql.parse(container => ...).
SELECT UPPER(DECODE(d.cdb, 'NO',
                    i.instance_name,
                    i.instance_name || '.' || SYS_CONTEXT('USERENV', 'CON_NAME'))),
       'PGA_info',
       p.name,  -- PGA metric (e.g. aggregate PGA auto target, freeable memory)
       p.value, -- Value
       p.unit   -- Unit of measurement
FROM v$pgastat p
         CROSS JOIN v$instance i
         CROSS JOIN v$database d
-- CDB$ROOT sees the rows of every container, a PDB only its own. Keep the
-- instance-wide set in the root - what the legacy plugin reported there - and
-- whatever a PDB shows of itself.
--
-- How much a PDB shows depends on the release, and the predicate covers both
-- without asking for the version: 23ai keeps per-container rows, so a PDB
-- reports its own figures (measured: process count 1 against 101 in the root),
-- while 21c only has con_id 0 and a PDB repeats the instance-wide numbers -
-- which is what the legacy plugin produced there as well.
WHERE SYS_CONTEXT('USERENV', 'CON_ID') <> '1'
   OR p.con_id = 0
