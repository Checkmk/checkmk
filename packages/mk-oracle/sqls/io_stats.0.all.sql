-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.

-- Section io_stats: provides a breakdown of I/O activity by file type
WITH iostat_file AS
         (
             SELECT con_id,
                    filetype_name,                                                    -- Type of file (datafile, logfile, controlfile, tempfile, etc.)
                    SUM(large_read_reqs)                     large_read_reqs,         -- Total number of large read requests issued
                    SUM(large_read_servicetime)              large_read_servicetime,  -- Total service time (microseconds) for large reads
                    SUM(large_write_reqs)                    large_write_reqs,        -- Total number of large write requests issued
                    SUM(large_write_servicetime)             large_write_servicetime, -- Total service time for large writes
                    SUM(small_read_reqs)                     small_read_reqs,         -- Total number of small read requests issued
                    SUM(small_read_servicetime)              small_read_servicetime,  -- Total service time for small reads
                    SUM(small_sync_read_reqs)                small_sync_read_reqs,    -- Total number of synchronous small reads
                    SUM(small_write_reqs)                    small_write_reqs,        -- Total number of small write requests issued
                    SUM(small_write_servicetime)             small_write_servicetime, -- Total service time for small writes
                    SUM(small_read_megabytes * 1024 * 1024)  small_read_bytes,        -- Bytes read via small I/O (converted from MB)
                    SUM(large_read_megabytes * 1024 * 1024)  large_read_bytes,        -- Bytes read via large I/O (converted from MB)
                    SUM(small_write_megabytes * 1024 * 1024) small_write_bytes,       -- Bytes written via small I/O (converted from MB)
                    SUM(large_write_megabytes * 1024 * 1024) large_write_bytes        -- Bytes written via large I/O (converted from MB)
             FROM v$iostat_file -- Dynamic performance view: aggregated I/O stats by file type
             GROUP BY con_id, filetype_name
         )
SELECT UPPER(
           DECODE(d.cdb, 'NO', i.instance_name, -- If non-CDB → just instance name
                  i.instance_name || '.' || vd.name) -- If CDB → instance name + container name
       )             AS instance_container,
       'iostat_file' AS metric_source, -- Label for this dataset (identifies as file I/O stats)
       filetype_name,                  -- File type (datafile, logfile, controlfile, tempfile, etc.)
       small_read_reqs,                -- Number of small read requests
       large_read_reqs,                -- Number of large read requests
       small_write_reqs,               -- Number of small write requests
       large_write_reqs,               -- Number of large write requests
       small_read_servicetime,         -- Total service time for small reads
       large_read_servicetime,         -- Total service time for large reads
       small_write_servicetime,        -- Total service time for small writes
       large_write_servicetime,        -- Total service time for large writes
       small_read_bytes,               -- Total bytes read by small I/O
       large_read_bytes,               -- Total bytes read by large I/O
       small_write_bytes,              -- Total bytes written by small I/O
       large_write_bytes               -- Total bytes written by large I/O
FROM iostat_file io
         JOIN v$containers vd ON io.con_id = vd.con_id -- Map container ID to container name
         JOIN v$instance i ON 1 = 1 -- Get instance details
         JOIN v$database d ON 1 = 1 -- Get database details (CDB flag)
ORDER BY vd.con_id,
         io.filetype_name