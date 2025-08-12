-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms AND
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section locks
SELECT UPPER(vp.name)
           || '|' || b.sid
           || '|' || b.serial#
           || '|' || b.machine
           || '|' || b.program
           || '|' || b.process
           || '|' || b.osuser
           || '|' || b.username
           || '|' || b.SECONDS_IN_WAIT
           || '|' || b.BLOCKING_SESSION_STATUS
           || '|' || bs.inst_id
           || '|' || bs.sid
           || '|' || bs.serial#
           || '|' || bs.machine
           || '|' || bs.program
           || '|' || bs.process
           || '|' || bs.osuser
           || '|' || bs.username
    FROM v$session b
    JOIN gv$session bs 
        ON bs.inst_id = b.BLOCKING_INSTANCE
            AND bs.sid = b.BLOCKING_SESSION
            AND bs.con_id = b.con_id
    JOIN ( SELECT vp.con_id
    ,i.instance_name || '.' || vp.name name
    FROM v$containers vp
                 JOIN v$instance i ON 1 = 1
                 JOIN v$database d ON 1=1
                 WHERE d.cdb = 'YES' AND vp.con_id <> 2
                UNION ALL
                 SELECT 0, instance_name
                 FROM v$instance
               ) vp ON b.con_id = vp.con_id
    where b.BLOCKING_SESSION is not null
UNION ALL
SELECT UPPER(i.instance_name || '.' || vp.name)
           || '|||||||||||||||||'
    FROM v$containers vp
    JOIN v$instance i 
        ON 1 = 1
    JOIN v$database d 
        ON 1=1
    WHERE d.cdb = 'YES' AND vp.con_id <> 2
UNION ALL
SELECT upper(i.instance_name)
           || '|||||||||||||||||'
FROM v$instance i