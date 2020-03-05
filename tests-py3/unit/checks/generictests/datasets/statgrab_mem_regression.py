#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'statgrab_mem'

info = [
    ['mem.cache', '0'], ['mem.total', '4294967296'], ['mem.free', '677666816'],
    ['mem.used', '3617300480'], ['swap.total', '8589934592'],
    ['swap.free', '4976402432'], ['swap.used', '3613532160']
]

discovery = {'': [(None, 'memused_default_levels')]}

checks = {
    '': [
        (
            None, (150.0, 200.0), [
                (
                    1,
                    'Total (RAM + Swap): 168% - 6.73 GB of 4.00 GB RAM (warn/crit at 150%/200% used)',
                    [
                        ('swap_used', 3613532160, None, None, 0, 8589934592),
                        ('mem_used', 3617300480, None, None, 0, 4294967296),
                        (
                            'mem_used_percent', 84.22183990478516, None, None,
                            0, 100.0
                        ),
                        (
                            'mem_lnx_total_used', 7230832640, 6442450944.0,
                            8589934592.0, 0, 12884901888
                        )
                    ]
                ), (0, 'RAM: 84.22% - 3.37 GB of 4.00 GB', []),
                (0, 'Swap: 42.07% - 3.37 GB of 8.00 GB', [])
            ]
        )
    ]
}
