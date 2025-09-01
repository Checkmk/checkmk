-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section recovery_area: retrieves the usage of the Oracle Fast Recovery Area (FRA)
SELECT UPPER(
               DECODE(NVL(:IGNORE_DB_NAME, 0), NULL, d.NAME, i.instance_name)
       )                                      AS instance_name,  -- Database name or Instance name (uppercase), depends on :IGNORE_DB_NAME
       ROUND((SPACE_USED - SPACE_RECLAIMABLE) /
             (CASE NVL(SPACE_LIMIT, 1)
                  WHEN 0 THEN 1
                  ELSE SPACE_LIMIT END) *
             100)                             AS pct_used,       -- FRA % used after subtracting reclaimable space
       ROUND(SPACE_LIMIT / 1024 / 1024)       AS fra_size_mb,    -- Total FRA size (MB)
       ROUND(SPACE_USED / 1024 / 1024)        AS used_mb,        -- FRA space currently used (MB)
       ROUND(SPACE_RECLAIMABLE / 1024 / 1024) AS reclaimable_mb, -- Space that can be reclaimed (MB)
       d.FLASHBACK_ON                                            -- Flashback Database enabled status (YES/NO)
FROM V$RECOVERY_FILE_DEST,
     v$database d,
     v$instance i