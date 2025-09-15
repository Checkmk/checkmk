-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

/*
    Section performance: retrieves high-level performance and workload metrics
    from different Oracle dynamic performance views.
    --
    Covers:
    - DB time / CPU usage (V$SYS_TIME_MODEL)
    - Buffer pool activity and waits (V$BUFFER_POOL_STATISTICS)
    - SGA component sizes (V$SGAINFO)
    - Library cache efficiency (parse & execution cache) (V$LIBRARYCACHE)
*/

-- === Section 1: CPU and DB Time Usage ===
SELECT UPPER(i.INSTANCE_NAME)   AS instance_name, -- Oracle instance name
       'sys_time_model'         AS metric_group,  -- Identifies the metric source
       s.STAT_NAME,                               -- 'DB time' or 'DB CPU'
       ROUND(s.value / 1000000) AS value_seconds  -- Convert microseconds to seconds
FROM v$instance i,
     v$sys_time_model s
WHERE s.stat_name IN ('DB time', 'DB CPU'); -- Key workload metrics

-- === Section 2: Buffer Pool Statistics (Cache Efficiency & Waits) ===
SELECT UPPER(i.INSTANCE_NAME),
       'buffer_pool_statistics', -- Metric group identifier
       b.name,                   -- Buffer pool name (DEFAULT, KEEP, RECYCLE)
       b.db_block_gets,          -- Number of single block (current mode) reads
       b.db_block_change,        -- Number of block changes made
       b.consistent_gets,        -- Logical reads (consistent mode)
       b.physical_reads,         -- Physical disk reads
       b.physical_writes,        -- Physical disk writes
       b.free_buffer_wait,       -- Waits for free buffers
       b.buffer_busy_wait        -- Contention waits for buffer access
FROM v$instance i,
     v$buffer_pool_statistics b;

-- === Section 3: SGA Memory Information ===
SELECT UPPER(i.INSTANCE_NAME),
       'SGA_info', -- Metric group identifier
       s.name,     -- Name of the SGA component (Shared pool, Buffer cache, etc.)
       s.bytes     -- Size in bytes
FROM v$sgainfo s,
     v$instance i;

-- === Section 4: Library Cache Efficiency ===
SELECT UPPER(i.INSTANCE_NAME),
       'librarycache',  -- Metric group identifier
       b.namespace,     -- Namespace (SQL AREA, TABLE/PROCEDURE, BODY, etc.)
       b.gets,          -- Number of lookups for objects
       b.gethits,       -- Number of successful lookups
       b.pins,          -- Executions of objects
       b.pinhits,       -- Successful executions from cache
       b.reloads,       -- Library cache reloads (indicates misses)
       b.invalidations  -- Invalidations of cached objects
FROM v$instance i,
     v$librarycache b;
