-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section logswitches
SELECT UPPER(i.instance_name)
           || '|' || logswitches
    FROM v$instance i ,
        (SELECT COUNT(1) logswitches
                 FROM v$loghist h , v$instance i
                 WHERE h.first_time > sysdate - 1/24
                    AND h.thread# = i.instance_number
        )