#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'netapp_api_aggr'

parsed = {
    'aggr1': {
        'size-total': '43025357561856',
        'size-available': '8721801302016',
        'aggregation': 'aggr1'
    },
    'aggr2': {
        'aggregation': 'aggr2'
    }
}

discovery = {'': [('aggr1', {})]}

checks = {
    '': [
        (
            'aggr1', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '79.73% used (31.2 of 39.1 TiB)', [
                        (
                            'fs_used', 32714420.56640625, 32825742.76875,
                            36928960.61484375, 0, 41032178.4609375
                        ),
                        ('fs_size', 41032178.4609375, None, None, None, None),
                        (
                            'fs_used_percent', 79.72869536417686, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
