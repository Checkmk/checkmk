-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section performance
SELECT UPPER(i.INSTANCE_NAME)
           || '|' || 'sys_time_model'
           || '|' || S.STAT_NAME
           || '|' || ROUND(s.value / 1000000)
FROM v$instance i, v$sys_time_model s
WHERE s.stat_name IN ('DB time', 'DB CPU')
-- ORDER BY s.stat_name
UNION ALL
SELECT UPPER(i.INSTANCE_NAME)
           || '|' || 'buffer_pool_statistics'
           || '|' || b.name
           || '|' || b.db_block_gets
           || '|' || b.db_block_change
           || '|' || b.consistent_gets
           || '|' || b.physical_reads
           || '|' || b.physical_writes
           || '|' || b.FREE_BUFFER_WAIT
           || '|' || b.BUFFER_BUSY_WAIT
FROM v$instance i, v$buffer_pool_statistics b
UNION ALL
SELECT UPPER(i.INSTANCE_NAME)
           || '|' || 'SGA_info'
           || '|' || s.name
           || '|' || s.bytes
FROM v$sgainfo s, v$instance i
UNION ALL
SELECT UPPER(i.INSTANCE_NAME)
           || '|' || 'librarycache'
           || '|' || b.namespace
           || '|' || b.gets
           || '|' || b.gethits
           || '|' || b.pins
           || '|' || b.pinhits
           || '|' || b.reloads
           || '|' || b.invalidations
FROM v$instance i, v$librarycache b