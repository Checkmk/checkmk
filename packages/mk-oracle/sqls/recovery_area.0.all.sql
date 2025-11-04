-- Copyright (C) 2025 Checkmk GmbH
--
-- Licensed under the Apache License, Version 2.0 (the "License")
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--    http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
--
-- SPDX-License-Identifier: Apache-2.0

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