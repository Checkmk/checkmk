-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section instance
SELECT UPPER(i.instance_name)
           || '|' || i.VERSION
           || '|' || i.STATUS
           || '|' || i.LOGINS
           || '|' || i.ARCHIVER
           || '|' || ROUND((SYSDATE - i.startup_time) * 24 * 60 * 60)
           || '|' || DBID
           || '|' || LOG_MODE
           || '|' || DATABASE_ROLE
           || '|' || FORCE_LOGGING
           || '|' || d.name
           || '|' || TO_CHAR(d.created, 'ddmmyyyyhh24mi')
           || '|' || i.host_name
    FROM v$instance i, v$database d