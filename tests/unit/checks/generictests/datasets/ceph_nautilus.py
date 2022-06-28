#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ceph_df'

info = [
    ['RAW', 'STORAGE:'],
    ['CLASS', 'SIZE', 'AVAIL', 'USED', 'RAW', 'USED', '%RAW', 'USED'],
    ['ssd', '84', 'TiB', '81', 'TiB', '2.9', 'TiB', '3.0', 'TiB', '3.52'],
    ['TOTAL', '84', 'TiB', '81', 'TiB', '2.9', 'TiB', '3.0', 'TiB', '3.52'],
    ['POOLS:'],
    [
        'POOL', 'ID', 'STORED', 'OBJECTS', 'USED', '%USED', 'MAX', 'AVAIL',
        'QUOTA', 'OBJECTS', 'QUOTA', 'BYTES', 'DIRTY', 'USED', 'COMPR',
        'UNDER', 'COMPR'
    ],
    [
        'glance-images', '1', '25', 'GiB', '5.88k', '75', 'GiB', '0.10', '25',
        'TiB', 'N/A', 'N/A', '5.88k', '0', 'B', '0', 'B'
    ],
    [
        'cinder-volumes', '2', '616', 'GiB', '158.31k', '1.8', 'TiB', '2.32',
        '25', 'TiB', 'N/A', 'N/A', '158.31k', '0', 'B', '0', 'B'
    ],
    [
        'nova-vms', '3', '349', 'GiB', '91.08k', '1.0', 'TiB', '1.32', '25',
        'TiB', 'N/A', 'N/A', '91.08k', '0', 'B', '0', 'B'
    ],
    [
        'cephfs_data', '4', '0', 'B', '0', '0', 'B', '0', '25', 'TiB', 'N/A',
        'N/A', '0', '0', 'B', '0', 'B'
    ],
    [
        'cephfs_metadata', '5', '15', 'KiB', '60', '969', 'KiB', '0', '25',
        'TiB', 'N/A', 'N/A', '60', '0', 'B', '0', 'B'
    ],
    [
        '.rgw.root', '6', '2.6', 'KiB', '6', '288', 'KiB', '0', '25', 'TiB',
        'N/A', 'N/A', '6', '0', 'B', '0', 'B'
    ],
    [
        'default.rgw.control', '7', '0', 'B', '8', '0', 'B', '0', '25', 'TiB',
        'N/A', 'N/A', '8', '0', 'B', '0', 'B'
    ],
    [
        'default.rgw.meta', '8', '0', 'B', '0', '0', 'B', '0', '25', 'TiB',
        'N/A', 'N/A', '0', '0', 'B', '0', 'B'
    ],
    [
        'default.rgw.log', '9', '0', 'B', '207', '0', 'B', '0', '25', 'TiB',
        'N/A', 'N/A', '207', '0', 'B', '0', 'B'
    ]
]

discovery = {
    '': [
        ('.rgw.root', {}), ('SUMMARY', {}), ('cephfs_data', {}),
        ('cephfs_metadata', {}), ('cinder-volumes', {}),
        ('default.rgw.control', {}), ('default.rgw.log', {}),
        ('default.rgw.meta', {}), ('glance-images', {}), ('nova-vms', {})
    ]
}

checks = {
    '': [
        (
            'SUMMARY', {
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
                    0, 'Used: 3.57% - 3.00 TiB of 84.0 TiB', [
                        (
                            'fs_used', 3145728.0, 70464307.2, 79272345.6, 0,
                            88080384.0
                        ), ('fs_size', 88080384.0, None, None, 0, None),
                        (
                            'fs_used_percent', 3.5714285714285716, 80.0, 90.0, 0.0, 100.0
                        )
                    ]
                )
            ]
        ),
        (
            '.rgw.root', {
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
                    0, 'Used: <0.01% - 2.60 KiB of 25.0 TiB', [
                        (
                            'fs_used', 0.0025390610098838806,
                            20971520.00203125, 23592960.002285156, 0,
                            26214400.00253906
                        ),
                        ('fs_size', 26214400.00253906, None, None, 0, None),
                        (
                            'fs_used_percent', 9.685749090720954e-09, 80.0, 90.0, 0.0, 100.0
                        )
                    ]
                )
            ]
        ),
        (
            'cephfs_data', {
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
                    0, 'Used: 0% - 0 B of 25.0 TiB', [
                        (
                            'fs_used', 0.0, 20971520.0, 23592960.0, 0,
                            26214400.0
                        ), ('fs_size', 26214400.0, None, None, 0, None),
                        ('fs_used_percent', 0.0, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            'cephfs_metadata', {
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
                    0, 'Used: <0.01% - 15.0 KiB of 25.0 TiB', [
                        (
                            'fs_used', 0.0146484375, 20971520.01171875,
                            23592960.013183594, 0, 26214400.014648438
                        ),
                        (
                            'fs_size', 26214400.014648438, None, None, 0,
                            None
                        ),
                        (
                            'fs_used_percent', 5.587935444570369e-08, 80.0, 90.0, 0.0, 100.0
                        )
                    ]
                )
            ]
        ),
        (
            'cinder-volumes', {
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
                    0, 'Used: 2.35% - 616 GiB of 25.6 TiB', [
                        (
                            'fs_used', 630784.0, 21476147.2, 24160665.6, 0,
                            26845184.0
                        ), ('fs_size', 26845184.0, None, None, 0, None),
                        (
                            'fs_used_percent', 2.3497101007018615, 80.0, 90.0, 0.0, 100.0
                        )
                    ]
                )
            ]
        ),
        (
            'default.rgw.control', {
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
                    0, 'Used: 0% - 0 B of 25.0 TiB', [
                        (
                            'fs_used', 0.0, 20971520.0, 23592960.0, 0,
                            26214400.0
                        ), ('fs_size', 26214400.0, None, None, 0, None),
                        ('fs_used_percent', 0.0, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            'default.rgw.log', {
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
                    0, 'Used: 0% - 0 B of 25.0 TiB', [
                        (
                            'fs_used', 0.0, 20971520.0, 23592960.0, 0,
                            26214400.0
                        ), ('fs_size', 26214400.0, None, None, 0, None),
                        ('fs_used_percent', 0.0, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            'default.rgw.meta', {
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
                    0, 'Used: 0% - 0 B of 25.0 TiB', [
                        (
                            'fs_used', 0.0, 20971520.0, 23592960.0, 0,
                            26214400.0
                        ), ('fs_size', 26214400.0, None, None, 0, None),
                        ('fs_used_percent', 0.0, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            'glance-images', {
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
                    0, 'Used: 0.10% - 25.0 GiB of 25.0 TiB', [
                        (
                            'fs_used', 25600.0, 20992000.0, 23616000.0, 0,
                            26240000.0
                        ), ('fs_size', 26240000.0, None, None, 0, None),
                        (
                            'fs_used_percent', 0.0975609756097561, 80.0, 90.0, 0.0, 100.0
                        )
                    ]
                )
            ]
        ),
        (
            'nova-vms', {
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
                    0, 'Used: 1.34% - 349 GiB of 25.3 TiB', [
                        (
                            'fs_used', 357376.0, 21257420.8, 23914598.4, 0,
                            26571776.0
                        ), ('fs_size', 26571776.0, None, None, 0, None),
                        (
                            'fs_used_percent', 1.344945855331612, 80.0, 90.0, 0.0, 100.0
                        )
                    ]
                )
            ]
        )
    ]
}
