-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

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
