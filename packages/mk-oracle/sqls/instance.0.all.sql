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

-- Section instance: summary of the current Oracle database's runtime status, configuration, and role
SELECT UPPER(i.instance_name),                           -- Instance name in uppercase (e.g., ORCL1)
       i.VERSION,                                        -- Oracle database version (e.g., 19.0.0.0.0)
       i.STATUS,                                         -- Instance status: STARTED, MOUNTED, OPEN
       i.LOGINS,                                         -- Login status: ALLOWED, RESTRICTED, DISABLED
       i.ARCHIVER,                                       -- Archive log status: STARTED, STOPPED, FAILED
       ROUND((SYSDATE - i.startup_time) * 24 * 60 * 60), -- Uptime in seconds since instance started
       DBID,                                             -- Database Identifier (unique per DB)
       LOG_MODE,                                         -- Archive log mode: ARCHIVELOG or NOARCHIVELOG
       DATABASE_ROLE,                                    -- Database role: PRIMARY, PHYSICAL STANDBY, etc.
       FORCE_LOGGING,                                    -- Indicates if FORCE LOGGING is enabled (YES/NO)
       d.name,                                           -- Database name
       TO_CHAR(d.created, 'ddmmyyyyhh24mi'),             -- Database creation date/time in custom format
       i.host_name                                       -- Hostname of the server running the instance
FROM v$instance i,
     v$database d -- Cross join used for combining instance and DB metadata