-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section dataguard_stats
SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name))
           ||'|'|| upper(d.DB_UNIQUE_NAME)
           ||'|'|| d.DATABASE_ROLE
           ||'|'|| ds.name
           ||'|'|| ds.value
           ||'|'|| d.SWITCHOVER_STATUS
           ||'|'|| d.DATAGUARD_BROKER
           ||'|'|| d.PROTECTION_MODE
           ||'|'|| d.FS_FAILOVER_STATUS
           ||'|'|| d.FS_FAILOVER_OBSERVER_PRESENT
           ||'|'|| d.FS_FAILOVER_OBSERVER_HOST
           ||'|'|| d.FS_FAILOVER_CURRENT_TARGET
           ||'|'|| ms.status
           ||'|'|| d.open_mode
    FROM  v$database d
    JOIN  v$parameter vp
        ON 1=1
    JOIN v$instance i
        ON 1=1
    LEFT OUTER JOIN v$dataguard_stats ds
        ON 1=1
    LEFT OUTER JOIN (
        SELECT listagg(to_char(inst_id) || '.' || status, ', ')
            WITHIN GROUP (ORDER BY to_char(inst_id) || '.' || status) status
            FROM gv$managed_standby
            WHERE PROCESS = 'MRP0'
            ) ms
        ON 1=1
    WHERE vp.name = 'log_archive_config'
        AND   vp.value IS NOT NULL
    ORDER BY 1