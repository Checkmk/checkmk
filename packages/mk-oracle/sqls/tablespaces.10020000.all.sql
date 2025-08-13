-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section tablespaces
SELECT UPPER(d.NAME)
        || '|' || file_name
        || '|' || tablespace_name
        || '|' || fstatus
        || '|' || autoextensible
        || '|' || blocks
        || '|' || maxblocks
        || '|' || user_blocks
        || '|' || increment_by
        || '|' || online_status
        || '|' || block_size
        || '|' || decode(tstatus,'READ ONLY', 'READONLY', tstatus)
        || '|' || free_blocks
        || '|' || contents
        || '|' || iversion
    FROM v$database d,
        v$instance i,
        (SELECT f.file_name,
                f.tablespace_name,
                f.status fstatus,
                f.autoextensible,
                f.blocks,
                f.maxblocks,
                f.user_blocks,
                f.increment_by,
                f.online_status,
                t.block_size,
                t.status tstatus,
                nvl(sum(fs.blocks),0) free_blocks,
                t.contents,
            (select version from v$instance) iversion
            FROM dba_data_files f,
                dba_tablespaces t,
                dba_free_space fs
            WHERE f.tablespace_name = t.tablespace_name
            AND f.file_id = fs.file_id(+)
            GROUP BY f.file_name,
                f.tablespace_name,
                f.status,
                f.autoextensible,
                f.blocks,
                f.maxblocks,
                f.user_blocks,
                f.increment_by,
                f.online_status,
                t.block_size,
                t.status,
                t.contents
        )
    WHERE d.database_role = 'PRIMARY'
UNION ALL
SELECT upper(dbf.name)
           || '|' || dbf.file_name
           || '|' || dbf.tablespace_name
           || '|' || dbf.fstatus
           || '|' || dbf.autoextensible
           || '|' || dbf.blocks
           || '|' || dbf.maxblocks
           || '|' || dbf.user_blocks
           || '|' || dbf.increment_by
           || '|' || dbf.online_status
           || '|' || dbf.block_size
           || '|' || decode(tstatus,'READ ONLY', 'READONLY', tstatus)
           || '|' || dbf.free_blocks
           || '|' || 'TEMPORARY'
           || '|' || i.version
    FROM v$database d
    JOIN v$instance i
        ON 1 = 1
    JOIN (
        SELECT vp.name,
                f.file_name,
                t.tablespace_name,
                f.status fstatus,
                f.autoextensible,
                f.blocks,
                f.maxblocks,
                f.user_blocks,
                f.increment_by,
                'ONLINE' online_status,
                t.block_size,
                t.status tstatus,
                f.blocks - nvl(SUM(tu.blocks),0) free_blocks,
                t.contents
            FROM dba_tablespaces t
            JOIN (SELECT 0, name FROM v$database) vp
                ON 1=1
            LEFT OUTER JOIN dba_temp_files f
                 ON t.tablespace_name = f.tablespace_name
            LEFT OUTER JOIN gv$tempseg_usage tu
                 ON f.tablespace_name = tu.tablespace
                 AND f.RELATIVE_FNO = tu.SEGRFNO#
            WHERE t.contents = 'TEMPORARY'
            GROUP BY vp.name,
                f.file_name,
                t.tablespace_name,
                f.status,
                f.autoextensible,
                f.blocks,
                f.maxblocks,
                f.user_blocks,
                f.increment_by,
                t.block_size,
                t.status,
                t.contents
    ) dbf
        ON 1 = 1
