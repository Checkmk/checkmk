#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'ucd_mem'


info = [['foobar', '8388604', '8388604', '64313712', '3845212', '12233816', '16000', '3163972', '30364', '10216780', '1', 'some error message']]

discovery = {'': [('', {})]}

checks = {
    '': [
        (
            None, {
                'levels_ram': ('perc_used', (20.0, 30.0)),
            }, [
                (1, u'Error: foobar', []), (1, u'some error message', []),
                (
                    2, 'RAM: 78.09% - 47.89 GB of 61.33 GB (warn/crit at 20.0%/30.0% used)',
                        [
                            ('mem_used', 51426668544, 13171448217.6, 19757172326.399998, 0, 65857241088),
                            ('mem_used_percent', 78.08810040384546, 20.0, 29.999999999999996, 0.0, None)
                        ]
                ),
                (0, 'Swap: 0% - 0.00 B of 8.00 GB', [
                    ('swap_used', 0, None, None, 0, 8589930496)]),
                (
                    0, 'Total virtual memory: 69.08% - 47.89 GB of 69.33 GB', []
                )

            ]
        )
    ]
}
