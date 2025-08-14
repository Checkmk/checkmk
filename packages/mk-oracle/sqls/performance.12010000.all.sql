-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section performance
SELECT UPPER(DECODE(cdb, 'NO', instance_name, instance_name || '.' || con_name))
           || '|' || 'sys_time_model'
           || '|' || STAT_NAME
           || '|' || ROUND(value / 1000000)
    FROM (
         SELECT d.cdb, i.instance_name, s.stat_name, s.value, vd.name con_name
             FROM v$instance i
             JOIN v$con_sys_time_model s ON s.stat_name IN ('DB time', 'DB CPU')
             JOIN v$containers vd ON vd.con_id = s.con_id
             JOIN v$database d ON d.cdb = 'YES'
             WHERE vd.con_id <> 2
         UNION ALL
         SELECT d.cdb, i.instance_name, s.stat_name, s.value, NULL
            FROM v$instance i
            JOIN v$sys_time_model s
                ON s.stat_name IN ('DB time', 'DB CPU')
            JOIN v$database d
                ON d.cdb = 'NO'
            ORDER BY stat_name
     )
UNION ALL
SELECT UPPER(DECODE(cdb, 'NO', instance_name, instance_name || '.' || con_name))
           || '|' || 'sys_wait_class'
           || '|' || WAIT_CLASS
           || '|' || ROUND(total_waits)
           || '|' || ROUND(time_waited)
           || '|' || ROUND(total_waits_fg)
           || '|' || ROUND(time_waited_fg)
    FROM (
         SELECT i.instance_name, vd.con_id, s.WAIT_CLASS, s.total_waits, s.time_waited, s.total_waits_fg, s.time_waited_fg, vd.name con_name, d.cdb
             FROM v$instance i
             JOIN v$database d
                 ON d.cdb = 'YES'
             JOIN v$containers vd
                 ON 1=1
             JOIN v$con_system_wait_class s
                 ON vd.con_id = s.con_id
             WHERE s.WAIT_CLASS <> 'Idle'
         UNION ALL
         SELECT i.instance_name, 0, s.WAIT_CLASS, s.total_waits, s.time_waited, s.total_waits_fg, s.time_waited_fg, NULL, d.cdb
            FROM v$instance i
            JOIN v$database d
                ON d.cdb = 'NO'
            JOIN v$system_wait_class s
                ON s.WAIT_CLASS <> 'Idle'
            ORDER BY con_name, wait_class
     )
UNION ALL
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.CDB$ROOT'))
           || '|' || 'buffer_pool_statistics'
           || '|' || b.name
           || '|' || b.db_block_gets
           || '|' || b.db_block_change
           || '|' || b.consistent_gets
           || '|' || b.physical_reads
           || '|' || b.physical_writes
           || '|' || b.FREE_BUFFER_WAIT
           || '|' || b.BUFFER_BUSY_WAIT
    FROM v$instance i
    JOIN v$buffer_pool_statistics b ON b.con_id = 0
    JOIN v$database d ON 1=1
UNION ALL
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.CDB$ROOT'))
           || '|' || 'SGA_info'
           || '|' || s.name
           || '|' || s.bytes
    FROM v$instance i
    JOIN v$sgainfo s ON s.con_id = 0
    JOIN v$database d ON 1=1
UNION ALL
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.CDB$ROOT'))
           || '|' || 'librarycache'
           || '|' || b.namespace
           || '|' || b.gets
           || '|' || b.gethits
           || '|' || b.pins
           || '|' || b.pinhits
           || '|' || b.reloads
           || '|' || b.invalidations
    FROM v$instance i
    JOIN v$librarycache b ON b.con_id = 0
    JOIN v$database d ON 1=1
UNION ALL
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.' || c.name))
           || '|PGA_info'
           || '|' || p.name
           || '|' || p.value
           || '|' || p.unit
    FROM v$containers c
    JOIN v$database d
        ON 1=1
    JOIN v$instance i
        ON 1=1
    JOIN v$pgastat p
        ON p.con_id = c.con_id
    WHERE c.con_id IN (
        SELECT con_id
            FROM v$containers
            WHERE c.open_mode LIKE 'READ %'
                AND c.name <> 'PDB$SEED'
    )
UNION ALL
SELECT UPPER(DECODE(d.cdb, 'NO', i.instance_name, i.instance_name || '.' || c.name))
           || '|PGA_info'
           || '|' || p.name
           || '|' || p.value
           || '|' || p.unit
    FROM v$containers c
    JOIN v$database d
        ON 1=1
    JOIN v$instance i
        ON 1=1
    JOIN v$pgastat p
        ON p.con_id = 0
    WHERE c.name = 'CDB$ROOT'