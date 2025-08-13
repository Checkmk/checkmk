-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section recovery_status
SELECT UPPER(DECODE(NVL(:IGNORE_DB_NAME, 0) , 0, DECODE(vp.con_id, null, d.NAME,d.NAME||'.'||vp.name)    , i.instance_name))
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
           ||'|'|| NVL(vb.STATUS, 'unknown')
           ||'|'|| NVL2(vb.TIME, round((sysdate-vb.TIME)*24*60*60), 0)
    FROM  v$datafile_header dh
        JOIN v$database d
            on 1=1
        JOIN v$instance i
            on 1=1
        LEFT OUTER JOIN v$backup vb
            on vb.file# = dh.file#
        LEFT OUTER JOIN V$PDBS vp on
            dh.con_id = vp.con_id
    ORDER BY dh.file#
