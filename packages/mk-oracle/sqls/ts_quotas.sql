-- Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section ts_quotas
    select upper(decode(NVL(:IGNORE_DB_NAME, 0), NULL, d.NAME, i.instance_name))
    {sep} Q.USERNAME
    {sep} Q.TABLESPACE_NAME
    {sep} Q.BYTES
    {sep} Q.MAX_BYTES
    from dba_ts_quotas Q, v$database d, v$instance i
    where max_bytes > 0
    union all
    select upper(decode(NVL(:IGNORE_DB_NAME, 0), 0, d.NAME, i.instance_name))
    {sep} '' {sep} '' {sep} ''
    from v$database d, v$instance i
    order by 1
