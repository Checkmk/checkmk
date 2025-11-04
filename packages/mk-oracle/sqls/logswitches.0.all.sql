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

-- Section logswitches: retrieves the number of redo log switches (log file changes) in the last one hour
SELECT UPPER(i.instance_name) AS instance_name, -- Current Oracle instance name (uppercased)
       logswitches                              -- Number of redo log switches in the last hour
FROM v$instance i,
     (SELECT COUNT(1) logswitches -- Count how many log switches occurred
      FROM v$loghist h, -- Historical log switch events
           v$instance i
      WHERE h.first_time > SYSDATE - 1 / 24 -- Only consider log switches in the last 1 hour
        AND h.thread# = i.instance_number -- Match redo thread to the current instance (RAC support)
     )
