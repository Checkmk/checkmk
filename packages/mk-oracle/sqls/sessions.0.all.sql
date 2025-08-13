-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section sessions
SELECT UPPER(i.instance_name)
        || '|' || CURRENT_UTILIZATION
        || '|' || LTRIM(LIMIT_VALUE)
        || '|' || MAX_UTILIZATION
    FROM v$resource_limit, v$instance i
    WHERE RESOURCE_NAME = 'sessions'