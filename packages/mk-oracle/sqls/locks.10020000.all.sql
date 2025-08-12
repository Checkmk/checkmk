-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section locks
SELECT UPPER(i.instance_name)
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
    JOIN v$instance i
        ON 1=1
    JOIN gv$session bs
        ON bs.inst_id = b.BLOCKING_INSTANCE
            AND bs.sid = b.BLOCKING_SESSION
    WHERE b.BLOCKING_SESSION IS NOT NULL
UNION ALL
SELECT UPPER(i.instance_name)
           || '|||||||||||||||||'
    FROM v$instance i
