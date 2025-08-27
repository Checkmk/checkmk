-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section resumable: monitors resumable space operations in the database
SELECT UPPER(i.instance_name), -- Instance name in uppercase
       u.username,             -- Database username owning the session
       a.SESSION_ID,           -- Session ID of the resumable operation
       a.status,               -- Current status (SUSPENDED, RESUMED, TIMEOUT)
       a.TIMEOUT,              -- Timeout in seconds before automatic resume/abort
       ROUND(
           (SYSDATE - TO_DATE(a.suspend_time, 'MM/DD/YY HH24:MI:SS')) * 24 * 60 * 60
       ),                      -- Elapsed time (seconds) since the session was suspended
       a.error_number,         -- Oracle error number that caused suspension
       TO_CHAR(
           TO_DATE(a.suspend_time, 'MM/DD/YY HH24:MI:SS'), 'MM/DD/YY_HH24:MI:SS'
       ),                      -- Formatted suspend timestamp
       a.resume_time,          -- Resume time (if resumed)
       a.error_msg             -- Error message text
FROM dba_resumable a,
     v$instance i,
     dba_users u
WHERE a.instance_id = i.instance_number -- Match resumable session to instance
  AND u.user_id = a.user_id             -- Match resumable session to user
  AND a.suspend_time IS NOT NULL        -- Only sessions that were actually suspended
UNION ALL
-- Dummy row to ensure instance name is always returned even if no resumable ops exist
SELECT UPPER(i.instance_name),
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL
FROM v$instance i
