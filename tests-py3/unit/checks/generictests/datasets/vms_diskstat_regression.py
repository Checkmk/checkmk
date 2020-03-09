#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'vms_diskstat'

info = [
    [u'$1$DGA1122:', u'TEST_WORK', u'1171743836', u'1102431184', u'0.00'],
    [u'DSA3:', u'SHAD_3', u'66048000', u'46137546', u'1.57'],
    [u'$1$DGA1123:', u'TEST_WORK', u'2171743836', u'1102431184', u'0.00'],
    [u'$1$DGA1124:', u'TEMP_02', u'3171743836', u'102431184', u'1.10'],
    [u'$1$DGA1125:', u'DATA_01', u'1171743836', u'202431184', u'0.20']
]

discovery = {
    'df':
    [(u'DATA_01', {}), (u'SHAD_3', {}), (u'TEMP_02', {}), (u'TEST_WORK', {})]
}

checks = {
    'df': [
        (
            u'DATA_01', {
                'trend_range': 24,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'magic_normsize': 20,
                'show_inodes': 'onlow',
                'levels': (80.0, 90.0),
                'show_reserved': False,
                'levels_low': (50.0, 60.0),
                'trend_perfdata': True
            }, [
                (
                    1,
                    '82.72% used (462.20 of 558.73 GB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'DATA_01', 473297.193359375, 457712.4359375,
                            514926.4904296875, 0, 572140.544921875
                        ),
                        ('fs_size', 572140.544921875, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'SHAD_3', {
                'trend_range': 24,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'magic_normsize': 20,
                'show_inodes': 'onlow',
                'levels': (80.0, 90.0),
                'show_reserved': False,
                'levels_low': (50.0, 60.0),
                'trend_perfdata': True
            }, [
                (
                    0, '30.15% used (9.49 of 31.49 GB)', [
                        (
                            u'SHAD_3', 9721.9013671875, 25800.0, 29025.0, 0,
                            32250.0
                        ), ('fs_size', 32250.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'TEMP_02', {
                'trend_range': 24,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'magic_normsize': 20,
                'show_inodes': 'onlow',
                'levels': (80.0, 90.0),
                'show_reserved': False,
                'levels_low': (50.0, 60.0),
                'trend_perfdata': True
            }, [
                (
                    2,
                    '96.77% used (1.43 of 1.48 TB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'TEMP_02', 1498687.818359375, 1238962.4359375,
                            1393832.7404296875, 0, 1548703.044921875
                        ),
                        ('fs_size', 1548703.044921875, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'TEST_WORK', {
                'trend_range': 24,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'magic_normsize': 20,
                'show_inodes': 'onlow',
                'levels': (80.0, 90.0),
                'show_reserved': False,
                'levels_low': (50.0, 60.0),
                'trend_perfdata': True
            }, [
                (
                    0, '5.92% used (33.05 of 558.73 GB)', [
                        (
                            u'TEST_WORK', 33844.068359375, 457712.4359375,
                            514926.4904296875, 0, 572140.544921875
                        ),
                        ('fs_size', 572140.544921875, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
