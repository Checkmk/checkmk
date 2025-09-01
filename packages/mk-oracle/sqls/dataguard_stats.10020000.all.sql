-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section dataguard_stats: Provides an overview of the current
-- Data Guard configuration, role, synchronization status, and failover readiness
SELECT UPPER(
               DECODE(
                       NVL(:IGNORE_DB_NAME, 0),
                       0, d.NAME,
                       i.instance_name
               )
       ),                              -- Outputs DB name or instance name depending on bind variable
       UPPER(d.DB_UNIQUE_NAME),        -- Unique name for Data Guard (can differ from DB_NAME)
       d.DATABASE_ROLE,                -- Role: PRIMARY, PHYSICAL STANDBY, LOGICAL STANDBY, etc.
       ds.name,                        -- Data Guard metric name (e.g., 'transport lag')
       ds.value,                       -- Value of the corresponding Data Guard metric
       d.SWITCHOVER_STATUS,            -- Indicates whether switchover is possible
       d.DATAGUARD_BROKER,             -- Indicates whether Data Guard Broker is enabled
       d.PROTECTION_MODE,              -- Protection mode: MAXIMUM PERFORMANCE, AVAILABILITY, etc.
       d.FS_FAILOVER_STATUS,           -- Fast-Start Failover status: ENABLED, DISABLED, etc.
       d.FS_FAILOVER_OBSERVER_PRESENT, -- Whether FSFO observer is connected (YES/NO)
       d.FS_FAILOVER_OBSERVER_HOST,    -- Hostname of FSFO observer if connected
       d.FS_FAILOVER_CURRENT_TARGET,   -- Current failover target configured
       ms.status,                      -- Aggregated MRP0 process status across RAC instances
       d.open_mode                     -- OPEN, MOUNTED, READ ONLY, etc.
FROM v$database d
         JOIN v$parameter vp ON 1 = 1 -- Dummy join to include a specific parameter filter
         JOIN v$instance i ON 1 = 1 -- Dummy join to get instance name
         LEFT OUTER JOIN v$dataguard_stats ds ON 1 = 1 -- Includes transport/recovery lag and other DG metrics
         LEFT OUTER JOIN (SELECT LISTAGG(TO_CHAR(inst_id) || '.' || status, ', ')
                                         WITHIN GROUP (ORDER BY TO_CHAR(inst_id) || '.' || status) AS status
                          FROM gv$managed_standby
                          WHERE PROCESS = 'MRP0' -- Multitenant Recovery Process for physical standby
                         ) ms ON 1 = 1
WHERE vp.name = 'log_archive_config' -- Ensures only Data Guard-enabled environments are included
  AND vp.value IS NOT NULL
ORDER BY 1 -- Sorts by instance or DB name