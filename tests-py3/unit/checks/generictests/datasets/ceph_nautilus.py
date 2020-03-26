#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
                    0, '3.57% used (3.00 of 84.00 TB)', [
                        (
                            'fs_used', 3145728.0, 70464307.2, 79272345.6, 0,
                            88080384.0
                        ), ('fs_size', 88080384.0, None, None, None, None)
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
                    0, '0.000001% used (288.00 kB of 25.00 TB)', [
                        (
                            'fs_used', 0.28125, 20971520.225, 23592960.253125,
                            0, 26214400.28125
                        ), ('fs_size', 26214400.28125, None, None, None, None)
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
                    0, '0% used (0.00 B of 25.00 TB)', [
                        (
                            'fs_used', 0.0, 20971520.0, 23592960.0, 0,
                            26214400.0
                        ), ('fs_size', 26214400.0, None, None, None, None)
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
                    0, '0.000004% used (969.00 kB of 25.00 TB)', [
                        (
                            'fs_used', 0.9462890625, 20971520.75703125,
                            23592960.851660155, 0, 26214400.946289062
                        ),
                        (
                            'fs_size', 26214400.946289062, None, None, None,
                            None
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
                    0, '6.72% used (1.80 of 26.80 TB)', [
                        (
                            'fs_used', 1887436.8000000007, 22481469.44,
                            25291653.12, 0, 28101836.8
                        ), ('fs_size', 28101836.8, None, None, None, None)
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
                    0, '0% used (0.00 B of 25.00 TB)', [
                        (
                            'fs_used', 0.0, 20971520.0, 23592960.0, 0,
                            26214400.0
                        ), ('fs_size', 26214400.0, None, None, None, None)
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
                    0, '0% used (0.00 B of 25.00 TB)', [
                        (
                            'fs_used', 0.0, 20971520.0, 23592960.0, 0,
                            26214400.0
                        ), ('fs_size', 26214400.0, None, None, None, None)
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
                    0, '0% used (0.00 B of 25.00 TB)', [
                        (
                            'fs_used', 0.0, 20971520.0, 23592960.0, 0,
                            26214400.0
                        ), ('fs_size', 26214400.0, None, None, None, None)
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
                    0, '0.29% used (75.00 GB of 25.07 TB)', [
                        (
                            'fs_used', 76800.0, 21032960.0, 23662080.0, 0,
                            26291200.0
                        ), ('fs_size', 26291200.0, None, None, None, None)
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
                    0, '3.85% used (1.00 of 26.00 TB)', [
                        (
                            'fs_used', 1048576.0, 21810380.8, 24536678.4, 0,
                            27262976.0
                        ), ('fs_size', 27262976.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
