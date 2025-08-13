-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section instance, asm version
-- ATTENTION: must be patched with the version column ${version_column} -> version_full for >= 18.0.0.0 otherwise version
SELECT UPPER(i.instance_name)
           || '|' || i.${version_column}
           || '|' || i.STATUS
           || '|' || i.LOGINS
           || '|' || i.ARCHIVER
           || '|' || ROUND((SYSDATE - i.startup_time) * 24 * 60 * 60)
           || '|' || '0'
           || '|' || 'NO'
           || '|' || 'ASM'
           || '|' || 'NO'
           || '|' || i.instance_name
           || '|' || i.host_name
    FROM v$instance i