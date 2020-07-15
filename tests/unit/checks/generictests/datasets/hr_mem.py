#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
from cmk.base.plugins.agent_based.hr_mem import parse_hr_mem  # type: ignore[import]


checkname = 'hr_mem'

parsed = parse_hr_mem([[
    [
        u'.1.3.6.1.2.1.25.2.1.2', u'Physical memory', u'1024', u'16282864',
        u'15982800'
    ],
    [
        u'.1.3.6.1.2.1.25.2.1.3', u'Virtual memory', u'1024', u'83391660',
        u'23477488'
    ],
    [
        u'.1.3.6.1.2.1.25.2.1.1', u'Memory buffers', u'1024', u'16282864',
        u'41984'
    ],
    [
        u'.1.3.6.1.2.1.25.2.1.1', u'Cached memory', u'1024', u'2777400',
        u'2777400'
    ],
    [
        u'.1.3.6.1.2.1.25.2.1.1', u'Shared memory', u'1024', u'1472764',
        u'1472764'
    ],
    [
        u'.1.3.6.1.2.1.25.2.1.3', u'Swap space', u'1024', u'67108796',
        u'7494688'
    ], [u'.1.3.6.1.2.1.25.2.1.4', u'/', u'4096', u'1015712', u'565297'],
    [u'.1.3.6.1.2.1.25.2.1.4', u'/dev/shm', u'4096', u'2035358', u'489277'],
    [u'.1.3.6.1.2.1.25.2.1.4', u'/boot', u'1024', u'122771', u'40827'],
    [u'.1.3.6.1.2.1.25.2.1.4', u'/bootmgr', u'1024', u'121779', u'296'],
    [u'.1.3.6.1.2.1.25.2.1.4', u'/config', u'1024', u'186243', u'24528'],
    [u'.1.3.6.1.2.1.25.2.1.4', u'/var', u'4096', u'7708143', u'675908'],
    [u'.1.3.6.1.2.1.25.2.1.4', u'/data', u'4096', u'93683381', u'64137121'],
    [u'.1.3.6.1.2.1.25.2.1.4', u'/run', u'4096', u'2035358', u'6'],
    [u'.1.3.6.1.2.1.25.2.1.4', u'/vtmp', u'4096', u'16384', u'2163']
]])

discovery = {'': [(None, 'memused_default_levels')]}

checks = {
    '': [
        (
            None, (150.0, 200.0), [
                (
                    0, 'Total (RAM + Swap): 126% - 19.70 GB of 15.53 GB RAM', [
                        ('swap_used', 7674560512, None, None, 0, 68719407104),
                        ('mem_used', 13479337984, None, None, 0, 16673652736),
                        (
                            'mem_used_percent', 80.84214177555005, None, None,
                            0, 100.0
                        ),
                        (
                            'mem_lnx_total_used', 21153898496, 25010479104.0,
                            33347305472.0, 0, 85393059840
                        )
                    ]
                ), (0, 'RAM: 80.84% - 12.55 GB of 15.53 GB', []),
                (0, 'Swap: 11.17% - 7.15 GB of 64.00 GB', [])
            ]
        ),
        (
            None, (1500, 2000), [
                (
                    2,
                    'Total (RAM + Swap): 126% - 19.70 GB of 15.53 GB RAM (warn/crit at 1.46 GB/1.95 GB used)',
                    [
                        ('swap_used', 7674560512, None, None, 0, 68719407104),
                        ('mem_used', 13479337984, None, None, 0, 16673652736),
                        (
                            'mem_used_percent', 80.84214177555005, None, None,
                            0, 100.0
                        ),
                        (
                            'mem_lnx_total_used', 21153898496, 1572864000.0,
                            2097152000.0, 0, 85393059840
                        )
                    ]
                ), (0, 'RAM: 80.84% - 12.55 GB of 15.53 GB', []),
                (0, 'Swap: 11.17% - 7.15 GB of 64.00 GB', [])
            ]
        )
    ]
}
