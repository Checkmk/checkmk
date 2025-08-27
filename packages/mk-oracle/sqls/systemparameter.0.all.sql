-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section systemparameter: retrieves all initialization/system parameters currently in effect for the Oracle instance
SELECT UPPER(i.instance_name), -- Database instance name in uppercase
       NAME,                   -- Parameter name (e.g., db_block_size, open_cursors)
       DISPLAY_VALUE,          -- Parameter value as displayed to users
       ISDEFAULT               -- Flag: 'TRUE' if default, 'FALSE' if explicitly set
FROM v$system_parameter, -- View showing system initialization parameters
     v$instance i        -- Instance information
WHERE NAME NOT LIKE '!_%' ESCAPE '!' -- Exclude hidden/internal parameters (start with "_")