-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section undostat
SELECT DECODE(vp.con_id, null, upper(i.INSTANCE_NAME)
           , UPPER(i.INSTANCE_NAME || '.' || vp.name))
           ||'|'|| ACTIVEBLKS
           ||'|'|| MAXCONCURRENCY
           ||'|'|| TUNED_UNDORETENTION
           ||'|'|| maxquerylen
           ||'|'|| NOSPACEERRCNT
    FROM v$instance i
    JOIN (
        SELECT * FROM v$undostat
            WHERE TUNED_UNDORETENTION > 0
            ORDER BY end_time desc
            FETCH next 1 rows only
        ) u
        ON 1=1
    LEFT OUTER JOIN v$pdbs vp
        ON vp.con_id = u.con_id