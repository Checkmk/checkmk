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

-- Section instance, asm version: Retrieves metadata about the currently running Oracle database instance
-- ATTENTION: must be patched with the version column ${version_column} -> version_full for >= 18.0.0.0 otherwise version
SELECT DISTINCT UPPER(c.instance_name),                           -- Instance name in uppercase (e.g., 'ORCL1')
                i.${version_column},                              -- Oracle version info (e.g., VERSION or VERSION_FULL)
                i.STATUS,                                         -- Current status of the instance (e.g., OPEN, MOUNT, STARTED)
                i.LOGINS,                                         -- Login status: ALLOWED, RESTRICTED, or DISABLED
                i.ARCHIVER,                                       -- Archive log mode: STARTED, STOPPED, FAILED
                ROUND((SYSDATE - i.startup_time) * 24 * 60 * 60), -- Uptime in seconds since instance startup
                '0',
                'NO',
                'ASM',
                'NO',
                c.instance_name,                                  -- Original (unmodified) instance name
                i.host_name                                       -- Host machine on which the instance is running
FROM gv$asm_client c
         JOIN gv$instance i ON c.inst_id = i.inst_id
         JOIN gv$database d ON c.db_name = d.name
