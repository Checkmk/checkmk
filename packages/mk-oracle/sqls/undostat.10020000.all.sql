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

-- Section undostat: retrieves the latest undo tablespace performance metrics
SELECT UPPER(i.INSTANCE_NAME) AS instance_name, -- Oracle instance name (uppercase)
       ACTIVEBLKS,                              -- Number of undo blocks active in the last interval
       MAXCONCURRENCY,                          -- Highest number of concurrent transactions
       TUNED_UNDORETENTION,                     -- Auto-tuned undo retention time (seconds)
       maxquerylen,                             -- Longest query execution length during the interval (seconds)
       NOSPACEERRCNT                            -- Number of times undo space could not be allocated
FROM v$instance i, -- Instance information
     (
         -- Subquery: Get the most recent undo statistics entry
         SELECT *
         FROM (SELECT *
               FROM v$undostat -- View of undo usage statistics (per 10 min interval typically)
               ORDER BY end_time DESC -- Sort by most recent snapshot
              )
         WHERE ROWNUM = 1 -- Only keep the latest record
           AND TUNED_UNDORETENTION > 0 -- Ensure auto-tuned undo retention is valid
     )
