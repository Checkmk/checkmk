-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section recovery_status
SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME,0), 0, d.NAME, i.instance_name))
           ||'|'|| d.DB_UNIQUE_NAME
           ||'|'|| d.DATABASE_ROLE
           ||'|'|| d.open_mode
           ||'|'|| dh.file#
           ||'|'|| round((dh.CHECKPOINT_TIME-to_date('01.01.1970','dd.mm.yyyy'))*24*60*60)
           ||'|'|| round((sysdate-dh.CHECKPOINT_TIME)*24*60*60)
           ||'|'|| dh.STATUS
           ||'|'|| dh.RECOVER
           ||'|'|| dh.FUZZY
           ||'|'|| dh.CHECKPOINT_CHANGE#
    FROM  v$datafile_header dh, v$database d, v$instance i
    ORDER BY dh.file#