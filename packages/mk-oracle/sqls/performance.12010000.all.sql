-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
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
- PGA statistics – per-PDB or root container memory usage.
*/

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
         ORDER BY stat_name
     );
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
         ORDER BY con_name, wait_class
     );
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
         JOIN v$database d ON 1 = 1;
-- === Section 4: SGA information ===
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.CDB$ROOT')),
       'SGA_info',
       s.name,  -- SGA component (Buffer Cache, Shared Pool, etc.)
       s.bytes  -- Size in bytes
FROM v$instance i
         JOIN v$sgainfo s ON s.con_id = 0
         JOIN v$database d ON 1 = 1;
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
         JOIN v$database d ON 1 = 1;
-- === Section 6: PGA statistics ===
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.' || c.name)),
       'PGA_info',
       p.name,  -- PGA metric (e.g., aggregate PGA auto target, freeable memory)
       p.value, -- Value
       p.unit   -- Unit of measurement
FROM v$containers c
         JOIN v$database d ON 1 = 1
         JOIN v$instance i ON 1 = 1
         JOIN v$pgastat p ON p.con_id = c.con_id
WHERE c.con_id IN (SELECT con_id
                   FROM v$containers
                   WHERE c.open_mode LIKE 'READ %' -- Only open/readable PDBs
                     AND c.name <> 'PDB$SEED'
                  );
-- === Special case for CDB$ROOT ===
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.' || c.name)),
       'PGA_info',
       p.name,
       p.value,
       p.unit
FROM v$containers c
         JOIN v$database d ON 1 = 1
         JOIN v$instance i ON 1 = 1
         JOIN v$pgastat p ON p.con_id = 0
WHERE c.name = 'CDB$ROOT'
