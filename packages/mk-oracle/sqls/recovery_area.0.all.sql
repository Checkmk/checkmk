-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section recovery_area
SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), NULL, d.NAME, i.instance_name))
           ||'|'|| round((SPACE_USED-SPACE_RECLAIMABLE)/
                         (CASE NVL(SPACE_LIMIT,1)
                             WHEN 0 THEN 1
                             ELSE SPACE_LIMIT END)*100)
           ||'|'|| round(SPACE_LIMIT/1024/1024)
           ||'|'|| round(SPACE_USED/1024/1024)
           ||'|'|| round(SPACE_RECLAIMABLE/1024/1024)
           ||'|'|| d.FLASHBACK_ON
FROM V$RECOVERY_FILE_DEST, v$database d, v$instance i