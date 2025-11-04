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

-- Section locks: retrieves blocking session information in an Oracle database
SELECT UPPER(i.instance_name) AS instance_name, -- Instance name
       b.sid,                                   -- Session ID of the blocked session
       b.serial#,                               -- Serial# of the blocked session
       b.machine,                               -- Client machine name of blocked session
       b.program,                               -- Program/application name of blocked session
       b.process,                               -- OS process ID of blocked session
       b.osuser,                                -- OS user of blocked session
       b.username,                              -- Oracle DB user of blocked session
       b.SECONDS_IN_WAIT,                       -- Seconds the session has been waiting
       b.BLOCKING_SESSION_STATUS,               -- Status of the blocking session (VALID, UNKNOWN, etc.)
       bs.inst_id,                              -- Instance ID of the blocking session (for RAC)
       bs.sid,                                  -- Session ID of the blocking session
       bs.serial#,                              -- Serial# of the blocking session
       bs.machine,                              -- Client machine name of blocking session
       bs.program,                              -- Program/application name of blocking session
       bs.process,                              -- OS process ID of blocking session
       bs.osuser,                               -- OS user of blocking session
       bs.username                              -- Oracle DB user of blocking session
FROM v$session b
         JOIN v$instance i
              ON 1 = 1
         JOIN gv$session bs
              ON bs.inst_id = b.BLOCKING_INSTANCE -- Match blocking session's instance (RAC support)
                  AND bs.sid = b.BLOCKING_SESSION -- Match blocking session's SID
WHERE b.BLOCKING_SESSION IS NOT NULL -- Only sessions that are blocked
UNION ALL
-- If no blocking sessions exist, return just the instance name with nulls
SELECT UPPER(i.instance_name),
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL,
       NULL
FROM v$instance i