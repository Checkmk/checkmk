-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section resumable
SELECT UPPER(i.instance_name)
        || '|' || u.username
        || '|' || a.SESSION_ID
        || '|' || a.status
        || '|' || a.TIMEOUT
        || '|' || round((sysdate-to_date(a.suspend_time,'MM/DD/YY HH24:MI:SS'))*24*60*60)
        || '|' || a.error_number
        || '|' || to_char(to_date(a.suspend_time, 'MM/DD/YY HH24:MI:SS'),'MM/DD/YY_HH24:MI:SS')
        || '|' || a.resume_time
        || '|' || a.error_msg
FROM dba_resumable a,
    v$instance i,
    dba_users u
WHERE a.instance_id = i.instance_number
    AND u.user_id = a.user_id
    AND a.suspend_time is not null
UNION ALL
SELECT UPPER(i.instance_name)
        || '|||||||||'
FROM v$instance i