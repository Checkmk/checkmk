-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section processes: retrieves the current process utilization of the instance
SELECT UPPER(i.instance_name),   -- Instance name in uppercase
       CURRENT_UTILIZATION,      -- Number of processes currently in use
       LTRIM(RTRIM(LIMIT_VALUE)) -- Configured maximum allowed processes
FROM v$resource_limit,
     v$instance i
WHERE RESOURCE_NAME = 'processes'
