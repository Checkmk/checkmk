-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section undostat
SELECT UPPER(i.INSTANCE_NAME)
       ||'|'|| ACTIVEBLKS
       ||'|'|| MAXCONCURRENCY
       ||'|'|| TUNED_UNDORETENTION
       ||'|'|| maxquerylen
       ||'|'|| NOSPACEERRCNT
    FROM v$instance i,
        (SELECT *
            FROM (SELECT * FROM v$undostat ORDER BY end_time DESC )
            WHERE rownum = 1 AND TUNED_UNDORETENTION > 0
        )