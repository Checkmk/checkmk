#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore

checkname = 'proxmox_vm_backup_status'

freeze_time = "2020-04-17 17:00:00"

info = [
    [
        '{"last_backup": {'
        '"archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-115-2020_04_16-22_20_43.vma.lzo", '
        '"archive_size": 4660039516, "started_time": "2020-04-16 22:20:43", "transfer_size": 90071629824, '
        '"transfer_time": 222}}'
    ],
]

discovery = {'': [(None, {})]}

checks = {
    '': [(
        None,
        {
            'age_levels_upper': (93600, 180000)
        },
        [
            (0, 'Age: 18 h', [('age', 67157.0, 93600.0, 180000.0, None, None)]),
            (0, 'Time: 2020-04-16 22:20:43', []),
            (0, 'Size: 4.34 GB', []),
            (0, 'Bandwidth: 386.93 MB/s', []),
        ],
    )]
}
