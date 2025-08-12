-- Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
-- This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
-- conditions defined in the file COPYING, which is part of this source code package.
-- Section asm_diskgroup
select STATE
           || '|' || TYPE
           || '|' || 'N'
           || '|' || sector_size
           || '|' || block_size
           || '|' || allocation_unit_size
           || '|' || total_mb
           || '|' || free_mb
           || '|' || required_mirror_free_mb
           || '|' || usable_file_mb
           || '|' || offline_disks
           || '|' || 'N'
           || '|' || name || '/'
from v$asm_diskgroup