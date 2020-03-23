#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'sap_hana_data_volume'

info = [
    [None, '[[H62 10]]'],
    [
        None, 'DATA', 'indexserver', '22',
        '/hana/data/H62/mnt00007/hdb00022/datavolume_0000.dat',
        '2111954886656', '2747705327616', '1553424617472', '2108828942336'
    ],
    [
        None, 'DATA', 'scriptserver', '20',
        '/hana/data/H62/mnt00007/hdb00020/datavolume_0000.dat',
        '2111954886656', '2747705327616', '88817664', '335544320'
    ],
    [
        None, 'DATA', 'xsengine', '21',
        '/hana/data/H62/mnt00007/hdb00021/datavolume_0000.dat',
        '2111954886656', '2747705327616', '89821184', '335544320'
    ]
]

discovery = {
    '': [
        ('H62 10 - DATA 20 Disk Net Data', {}), ('H62 10 - DATA 20 Disk', {}),
        ('H62 10 - DATA 20', {}), ('H62 10 - DATA 21 Disk Net Data', {}),
        ('H62 10 - DATA 21 Disk', {}), ('H62 10 - DATA 21', {}),
        ('H62 10 - DATA 22 Disk Net Data', {}), ('H62 10 - DATA 22 Disk', {}),
        ('H62 10 - DATA 22', {})
    ]
}

checks = {
    '': [
        (
            'Netdata H62 10 - DATA 20 Disk', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, []
        ),
        (
            'Netdata H62 10 - DATA 21 Disk', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, []
        ),
        (
            'Netdata H62 10 - DATA 22 Disk', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, []
        ),
        (
            'Volume H62 10 - DATA 20 Disk', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, []
        ),
        (
            'Volume H62 10 - DATA 20', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, []
        ),
        (
            'Volume H62 10 - DATA 21 Disk', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, []
        ),
        (
            'Volume H62 10 - DATA 21', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, []
        ),
        (
            'Volume H62 10 - DATA 22 Disk', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, []
        ),
        (
            'Volume H62 10 - DATA 22', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, []
        ),
        (
            'H62 10 - DATA 20 Disk', {
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
                    0, '76.86% used (1.92 of 2.50 TB)', [
                        (
                            'fs_used', 2014117.1328125, 2096332.8, 2358374.4,
                            0, 2620416.0
                        ), ('fs_size', 2620416.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'H62 10 - DATA 20', {
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
                    0, '26.47% used (84.70 of 320.00 MB)', [
                        ('fs_used', 84.703125, 256.0, 288.0, 0, 320.0),
                        ('fs_size', 320.0, None, None, None, None)
                    ]
                ), (0, 'Service: scriptserver', []),
                (
                    0,
                    'Path: /hana/data/H62/mnt00007/hdb00020/datavolume_0000.dat',
                    []
                )
            ]
        ),
        (
            'H62 10 - DATA 21 Disk', {
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
                    0, '76.86% used (1.92 of 2.50 TB)', [
                        (
                            'fs_used', 2014117.1328125, 2096332.8, 2358374.4,
                            0, 2620416.0
                        ), ('fs_size', 2620416.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'H62 10 - DATA 21', {
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
                    0, '26.77% used (85.66 of 320.00 MB)', [
                        ('fs_used', 85.66015625, 256.0, 288.0, 0, 320.0),
                        ('fs_size', 320.0, None, None, None, None)
                    ]
                ), (0, 'Service: xsengine', []),
                (
                    0,
                    'Path: /hana/data/H62/mnt00007/hdb00021/datavolume_0000.dat',
                    []
                )
            ]
        ),
        (
            'H62 10 - DATA 22 Disk', {
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
                    0, '76.86% used (1.92 of 2.50 TB)', [
                        (
                            'fs_used', 2014117.1328125, 2096332.8, 2358374.4,
                            0, 2620416.0
                        ), ('fs_size', 2620416.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'H62 10 - DATA 22', {
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
                    0, '73.66% used (1.41 of 1.92 TB)', [
                        (
                            'fs_used', 1481461.16015625, 1608908.8, 1810022.4,
                            0, 2011136.0
                        ), ('fs_size', 2011136.0, None, None, None, None)
                    ]
                ), (0, 'Service: indexserver', []),
                (
                    0,
                    'Path: /hana/data/H62/mnt00007/hdb00022/datavolume_0000.dat',
                    []
                )
            ]
        ),
        (
            'H62 10 - DATA 20 Disk Net Data', {
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
                    0, '0.003% used (84.70 MB of 2.50 TB)', [
                        (
                            'fs_used', 84.703125, 2096332.8, 2358374.4, 0,
                            2620416.0
                        ), ('fs_size', 2620416.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'H62 10 - DATA 21 Disk Net Data', {
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
                    0, '0.003% used (85.66 MB of 2.50 TB)', [
                        (
                            'fs_used', 85.66015625, 2096332.8, 2358374.4, 0,
                            2620416.0
                        ), ('fs_size', 2620416.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'H62 10 - DATA 22 Disk Net Data', {
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
                    0, '56.54% used (1.41 of 2.50 TB)', [
                        (
                            'fs_used', 1481461.16015625, 2096332.8, 2358374.4,
                            0, 2620416.0
                        ), ('fs_size', 2620416.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
