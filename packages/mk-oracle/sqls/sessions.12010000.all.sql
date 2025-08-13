-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section sessions
SELECT UPPER(vp.name)
           || '|' || LTRIM(COUNT(1))
           || DECODE(vp.con_id, 0, '|' || LTRIM(RTRIM(LIMIT_VALUE)) || '|-1')
    FROM (
        SELECT vp.con_id, i.instance_name || '.' || vp.name name
            FROM v$containers vp
            JOIN v$instance i
                ON 1 = 1
            JOIN v$database d
                ON 1 = 1
            WHERE d.cdb = 'YES' AND vp.con_id <> 2
        UNION ALL
        SELECT 0, instance_name
            FROM v$instance
    ) vp
    JOIN v$resource_limit rl
        ON RESOURCE_NAME = 'sessions'
    LEFT OUTER JOIN v$session vs
        ON vp.con_id = vs.con_id
    GROUP BY vp.name, vp.con_id, rl.LIMIT_VALUE
    ORDER BY 1