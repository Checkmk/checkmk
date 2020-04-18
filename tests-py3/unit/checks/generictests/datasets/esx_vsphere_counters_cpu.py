#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'esx_vsphere_counters'

info = [
    [u'cpu.costop', u'', u'1200', u'millisecond'],
    [u'cpu.ready', u'', u'2019', u'millisecond']
]

discovery = {
    '': [],
    'ramdisk': [],
    'uptime': [],
    'diskio': [],
    'cpu': [(None, {})],
    'if': [],
    'swap': [(None, {})],
}

checks = {
    'cpu': [
        (
            None, {}, [
                (
                    0, 'CPU ready: 10.1%', [
                        ('cpu_ready_percent', 10.095, None, None, None, None)
                    ]
                ),
                (
                    0, 'Co-Stop: 6.0%', [
                        ('cpu_costop_percent', 6.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            None, {'cpu_costop': (5.0, 10.0), 'cpu_ready': (5.0, 10.0)}, [
                (
                    2, 'CPU ready: 10.1% (warn/crit at 5.0%/10.0%)', [
                        ('cpu_ready_percent', 10.095, 5.0, 10.0, None, None)
                    ]
                ),
                (
                    1, 'Co-Stop: 6.0% (warn/crit at 5.0%/10.0%)', [
                        ('cpu_costop_percent', 6.0, 5.0, 10.0, None, None)
                    ]
                )
            ]
        )
    ]
}
