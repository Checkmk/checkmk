#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'emc_ecs_mem'

info = [
    [
        u'swap', u'8388604', u'8388604', u'64313712', u'3715272', u'12103876',
        u'16000', u'3213064', u'51260', u'15342316', u'0', u''
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'levels': (150.0, 200.0)
            }, [
                (
                    0, 'Total (RAM + Swap): 57.32% - 35.16 GB of 61.33 GB RAM',
                    [
                        ('swap_used', 0, None, None, 0, 8589930496),
                        ('mem_used', 37752340480, None, None, 0, 65857241088),
                        (
                            'mem_used_percent', 57.32450958514104, None, None,
                            0, 100.0
                        ),
                        (
                            'mem_lnx_total_used', 37752340480, 98785861632.0,
                            131714482176.0, 0, 74447171584
                        )
                    ]
                ), (0, 'RAM: 57.32% - 35.16 GB of 61.33 GB', []),
                (0, 'Swap: 0% - 0.00 B of 8.00 GB', []),
                (0, '', [('swap_used', 0, 8372604.0, 8372604.0, None, None)]),
                (
                    0, '', [
                        ('mem_lnx_cached', 15342316, None, None, None, None),
                        ('mem_lnx_buffers', 51260, None, None, None, None),
                        ('mem_lnx_shmem', 3213064, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
