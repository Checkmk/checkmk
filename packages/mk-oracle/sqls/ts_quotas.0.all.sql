-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section ts_quotas: retrieves tablespace quotas assigned to database users
-- Main query: Fetch user tablespace quotas
SELECT UPPER(
               DECODE(NVL(:IGNORE_DB_NAME, 0), NULL, d.NAME, i.instance_name)
       ) AS db_or_instance_name,
       Q.USERNAME,        -- Database user
       Q.TABLESPACE_NAME, -- Tablespace assigned to the user
       Q.BYTES,           -- Current space (in bytes) allocated to the user
       Q.MAX_BYTES        -- Maximum quota assigned to the user (in bytes)
FROM dba_ts_quotas Q, -- View containing per-user tablespace quotas
     v$database d,    -- Database information
     v$instance i     -- Instance information
WHERE max_bytes > 0; -- Only users with quotas > 0

-- Fallback query: If no user quotas exist, still return DB info
SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name)) AS db_or_instance_name,
       NULL, -- No user
       NULL, -- No tablespace
       NULL, -- No bytes
       NULL  -- No max quota
FROM v$database d,
     v$instance i

ORDER BY 1 -- Sort by database/instance name
