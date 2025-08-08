-- Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section io_stats
WITH iostat_file AS (
    SELECT con_id,
           filetype_name,
           SUM(large_read_reqs) large_read_reqs,
           SUM(large_read_servicetime) large_read_servicetime,
           SUM(large_write_reqs) large_write_reqs,
           SUM(large_write_servicetime) large_write_servicetime,
           SUM(small_read_reqs) small_read_reqs,
           SUM(small_read_servicetime) small_read_servicetime,
           SUM(small_sync_read_reqs) small_sync_read_reqs,
           SUM(small_write_reqs) small_write_reqs,
           SUM(small_write_servicetime) small_write_servicetime,
           SUM(small_read_megabytes * 1024 * 1024) small_read_bytes,
           SUM(large_read_megabytes * 1024 * 1024) large_read_bytes,
           SUM(small_write_megabytes * 1024 * 1024) small_write_bytes,
           SUM(large_write_megabytes * 1024 * 1024) large_write_bytes
    FROM v$iostat_file
    GROUP BY con_id,
             filetype_name
)
SELECT upper(
               DECODE(
                       d.cdb,
                       'NO',
                       i.instance_name,
                       i.instance_name || '.' || vd.name
               )
       )
    {sep} 'iostat_file'
                {sep} filetype_name
                {sep} small_read_reqs
                {sep} large_read_reqs
                {sep} small_write_reqs
                {sep} large_write_reqs
                {sep} small_read_servicetime
                {sep} large_read_servicetime
                {sep} small_write_servicetime
                {sep} large_write_servicetime
                {sep} small_read_bytes
                {sep} large_read_bytes
                {sep} small_write_bytes
                {sep} large_write_bytes
FROM iostat_file io
    JOIN v$containers vd ON io.con_id = vd.con_id
    JOIN v$instance i ON 1 = 1
    JOIN v$database d ON 1 = 1
ORDER BY vd.con_id,
    io.filetype_name