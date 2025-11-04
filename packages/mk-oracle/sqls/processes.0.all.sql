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

-- Section processes: retrieves the current process utilization of the instance
SELECT UPPER(i.instance_name),   -- Instance name in uppercase
       CURRENT_UTILIZATION,      -- Number of processes currently in use
       LTRIM(RTRIM(LIMIT_VALUE)) -- Configured maximum allowed processes
FROM v$resource_limit,
     v$instance i
WHERE RESOURCE_NAME = 'processes'
