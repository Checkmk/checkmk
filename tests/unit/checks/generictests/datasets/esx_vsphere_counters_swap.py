#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.esx_vsphere_counters import parse_esx_vsphere_counters

checkname = 'esx_vsphere_counters'

parsed = parse_esx_vsphere_counters([
    ['mem.swapin', '', '0', 'kiloBytes'],
    ['mem.swapout', '', '', 'kiloBytes'],
    ['mem.swapused', '', '0', 'kiloBytes'],
])

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
                (0, 'Swap in: 0 B', []), (0, 'Swap out: not available', []),
                (0, 'Swap used: 0 B', [])
            ]
        )
    ]
}
