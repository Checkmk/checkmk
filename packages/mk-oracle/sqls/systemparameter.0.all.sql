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

-- Section systemparameter: retrieves all initialization/system parameters currently in effect for the Oracle instance
SELECT UPPER(i.instance_name), -- Database instance name in uppercase
       NAME,                   -- Parameter name (e.g., db_block_size, open_cursors)
       DISPLAY_VALUE,          -- Parameter value as displayed to users
       ISDEFAULT               -- Flag: 'TRUE' if default, 'FALSE' if explicitly set
FROM v$system_parameter, -- View showing system initialization parameters
     v$instance i        -- Instance information
WHERE NAME NOT LIKE '!_%' ESCAPE '!' -- Exclude hidden/internal parameters (start with "_")