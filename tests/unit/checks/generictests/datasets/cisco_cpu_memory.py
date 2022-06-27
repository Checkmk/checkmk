#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'cisco_cpu_memory'

info = [
    [[u'11000', u'3343553', u'565879', u'284872']],
    [
        [u'1', u'Virtual Stack'],
        [u'25', u'Switch1 Container of Power Supply Bay'],
        [u'11000', u'Switch2 Supervisor 1 (virtual slot 11)']
    ]
]

discovery = {'': [(u'Switch2 Supervisor 1 (virtual slot 11)', {})]}

checks = {
    '': [
        (
            u'Switch2 Supervisor 1 (virtual slot 11)', {}, [
                (
                    0, 'Usage: 92.81% - 3.46 GiB of 3.73 GiB',
                    [('mem_used_percent', 92.81207602536634, None, None, 0.0, None)]
                )
            ]
        ),
        (
            u'Switch2 Supervisor 1 (virtual slot 11)', {
                'levels': (-2000, -1000)
            }, [
                (
                    2,
                    'Usage: 92.81% - 3.46 GiB of 3.73 GiB (warn/crit below 1.95 GiB/1000 MiB free)',
                    [
                        (
                            'mem_used_percent', 92.81207602536634, 47.61387331970475,
                            73.80693665985237, 0.0, None
                        )
                    ]
                )
            ]
        ),
        (
            u'Switch2 Supervisor 1 (virtual slot 11)', {
                'levels': (50.0, 90.0)
            }, [
                (
                    2,
                    'Usage: 92.81% - 3.46 GiB of 3.73 GiB (warn/crit at 50.00%/90.00% used)',
                    [('mem_used_percent', 92.81207602536634, 50.0, 90.0, 0.0, None)]
                )
            ]
        ),
        (
            u'Switch2 Supervisor 1 (virtual slot 11)', {
                'levels': (-20.0, -10.0)
            }, [
                (
                    2,
                    'Usage: 92.81% - 3.46 GiB of 3.73 GiB (warn/crit below 20.00%/10.00% free)',
                    [('mem_used_percent', 92.81207602536634, 80.0, 89.99999999999999, 0.0, None)]
                )
            ]
        )
    ]
}
