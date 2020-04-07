#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'esx_vsphere_counters'

info = [
    ['mem.swapin', '', '0', 'kiloBytes'],
    ['mem.swapout', '', '0', 'kiloBytes'],
    ['mem.swapused', '', '0', 'kiloBytes']
]

discovery = {
    'cpu': [],
    'diskio': [],
    '': [],
    'if': [],
    'uptime': [],
    'ramdisk': [],
    'swap': [(None, {})]
}

checks = {
    'swap': [
        (
            None, {}, [
                (0, 'Swap in: 0.00 KB', []), (0, 'Swap out: 0.00 KB', []),
                (0, 'Swap used: 0.00 KB', [])
            ]
        )
    ]
}
