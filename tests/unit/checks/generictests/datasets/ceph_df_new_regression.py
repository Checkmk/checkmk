#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ceph_df'

info = [
    ['GLOBAL:'], ['SIZE', 'AVAIL', 'RAW', 'USED', '%RAW', 'USED', 'OBJECTS'],
    ['873TiB', '779TiB', '94.2TiB', '10.79', '11.26M'], ['POOLS:'],
    [
        'NAME', 'ID', 'QUOTA', 'OBJECTS', 'QUOTA', 'BYTES', 'USED', '%USED',
        'MAX', 'AVAIL', 'OBJECTS', 'DIRTY', 'READ', 'WRITE', 'RAW', 'USED'
    ],
    [
        '.rgw.root', '1', 'N/A', 'N/A', '11.1KiB', '0', '242TiB', '61', '61',
        '11.7KiB', '219B', '33.4KiB'
    ],
    [
        'default.rgw.control', '2', 'N/A', 'N/A', '0B', '0', '242TiB', '8',
        '8', '0B', '0B', '0B'
    ],
    [
        'default.rgw.meta', '3', 'N/A', 'N/A', '73.6KiB', '0', '242TiB', '252',
        '252', '257KiB', '6.96KiB', '221KiB'
    ],
    [
        'default.rgw.log', '4', 'N/A', 'N/A', '149B', '0', '242TiB', '406',
        '406', '19.0MiB', '12.7MiB', '447B'
    ],
    [
        'rbd-rub.ec', '5', 'N/A', 'N/A', '19.4TiB', '3.43', '544TiB',
        '5086154', '5.09M', '12B', '292MiB', '25.8TiB'
    ],
    [
        'rbd', '6', 'N/A', 'N/A', '21.5TiB', '8.17', '242TiB', '5695802',
        '5.70M', '42.9MiB', '403MiB', '64.6TiB'
    ],
    [
        'ceph-bench', '7', 'N/A', 'N/A', '6.21GiB', '0', '242TiB', '1591',
        '1.59k', '0B', '3.11KiB', '18.6GiB'
    ],
    [
        'rados-bench.ec', '8', 'N/A', 'N/A', '6.59GiB', '0', '544TiB', '1684',
        '1.68k', '0B', '3.29KiB', '8.78GiB'
    ],
    [
        'rados-bench-ude.ec', '9', 'N/A', 'N/A', '6.60GiB', '0', '544TiB',
        '1687', '1.69k', '0B', '3.29KiB', '8.80GiB'
    ],
    [
        'default.rgw.buckets.index', '10', 'N/A', 'N/A', '0B', '0', '242TiB',
        '589', '589', '4.37MiB', '59.4MiB', '0B'
    ],
    [
        'default.rgw.buckets.data', '11', 'N/A', 'N/A', '425GiB', '0.17',
        '242TiB', '465820', '465.82k', '420KiB', '1.40MiB', '1.25TiB'
    ],
    [
        'default.rgw.buckets.non-ec', '12', 'N/A', 'N/A', '0B', '0', '242TiB',
        '5', '5', '339KiB', '368KiB', '0B'
    ],
    [
        'scbench', '13', 'N/A', 'N/A', '2.32GiB', '0', '242TiB', '596', '596',
        '1B', '2.05KiB', '6.97GiB'
    ],
    [
        'rub-s3.ec', '16', 'N/A', 'N/A', '4.88KiB', '0', '272TiB', '1000',
        '1k', '0B', '1002B', '6.51KiB'
    ]
]

discovery = {
    '': [
        ('.rgw.root', {}), ('SUMMARY', {}), ('ceph-bench', {}),
        ('default.rgw.buckets.data', {}), ('default.rgw.buckets.index', {}),
        ('default.rgw.buckets.non-ec', {}), ('default.rgw.control', {}),
        ('default.rgw.log', {}), ('default.rgw.meta', {}),
        ('rados-bench-ude.ec', {}), ('rados-bench.ec', {}), ('rbd', {}),
        ('rbd-rub.ec', {}), ('rub-s3.ec', {}), ('scbench', {})
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
                    0, 'Used: 10.77% - 94.0 TiB of 873 TiB', [
                        (
                            'fs_used', 98566144.0, 732325478.4, 823866163.2, 0,
                            None
                        ), ('fs_free', 816840704.0, None, None, 0, None),
                        (
                            'fs_used_percent', 10.767468499427263, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 915406848.0, None, None, 0, None)
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
                    0, 'Used: <0.01% - 11.1 KiB of 242 TiB', [
                        (
                            'fs_used', 0.010839849710464478,
                            203004313.60867187, 228379852.80975586, 0, None
                        ), ('fs_free', 253755392.0, None, None, 0, None),
                        (
                            'fs_used_percent', 4.271771182699213e-09, 80.0, 90.0, 0.0, 100.0
                        ),
                        ('fs_size', 253755392.01083985, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'ceph-bench', {
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
                    0, 'Used: <0.01% - 6.21 GiB of 242 TiB', [
                        (
                            'fs_used', 6359.039999991655, 203009400.83200002,
                            228385575.936, 0, None
                        ), ('fs_free', 253755392.0, None, None, 0, None),
                        (
                            'fs_used_percent', 0.0025059095682979, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 253761751.04, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'default.rgw.buckets.data', {
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
                    0, 'Used: 0.17% - 425 GiB of 242 TiB', [
                        (
                            'fs_used', 435200.0, 203352473.6, 228771532.8, 0,
                            None
                        ), ('fs_free', 253755392.0, None, None, 0, None),
                        (
                            'fs_used_percent', 0.1712101130792441, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 254190592.0, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'default.rgw.buckets.index', {
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
                    0, 'Used: 0% - 0 B of 242 TiB', [
                        ('fs_used', 0.0, 203004313.6, 228379852.8, 0, None),
                        ('fs_free', 253755392.0, None, None, 0, None),
                        ('fs_used_percent', 0.0, 80.0, 90.0, 0.0, 100.0),
                        ('fs_size', 253755392.0, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'default.rgw.buckets.non-ec', {
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
                    0, 'Used: 0% - 0 B of 242 TiB', [
                        ('fs_used', 0.0, 203004313.6, 228379852.8, 0, None),
                        ('fs_free', 253755392.0, None, None, 0, None),
                        ('fs_used_percent', 0.0, 80.0, 90.0, 0.0, 100.0),
                        ('fs_size', 253755392.0, None, None, 0, None)
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
                    0, 'Used: 0% - 0 B of 242 TiB', [
                        ('fs_used', 0.0, 203004313.6, 228379852.8, 0, None),
                        ('fs_free', 253755392.0, None, None, 0, None),
                        ('fs_used_percent', 0.0, 80.0, 90.0, 0.0, 100.0),
                        ('fs_size', 253755392.0, None, None, 0, None)
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
                    0, 'Used: <0.01% - 149 B of 242 TiB', [
                        (
                            'fs_used', 0.00014209747314453125,
                            203004313.6001137, 228379852.80012786, 0, None
                        ), ('fs_free', 253755392.0, None, None, 0, None),
                        (
                            'fs_used_percent', 5.5997814282681994e-11, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 253755392.0001421, None, None, 0, None)
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
                    0, 'Used: <0.01% - 73.6 KiB of 242 TiB', [
                        (
                            'fs_used', 0.07187500596046448, 203004313.6575,
                            228379852.8646875, 0, None
                        ), ('fs_free', 253755392.0, None, None, 0, None),
                        (
                            'fs_used_percent', 2.832452361844048e-08, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 253755392.071875, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'rados-bench-ude.ec', {
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
                    0, 'Used: <0.01% - 6.60 GiB of 544 TiB', [
                        (
                            'fs_used', 6758.399999976158, 456345681.92,
                            513388892.16, 0, None
                        ), ('fs_free', 570425344.0, None, None, 0, None),
                        (
                            'fs_used_percent', 0.0011847860545613218, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 570432102.4, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'rados-bench.ec', {
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
                    0, 'Used: <0.01% - 6.59 GiB of 544 TiB', [
                        (
                            'fs_used', 6748.159999966621, 456345673.7279999,
                            513388882.94399995, 0, None
                        ), ('fs_free', 570425344.0, None, None, 0, None),
                        (
                            'fs_used_percent', 0.0011829909454101745, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 570432092.16, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'rbd', {
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
                    0, 'Used: 8.16% - 21.5 TiB of 264 TiB', [
                        (
                            'fs_used', 22544384.0, 221039820.8, 248669798.4, 0,
                            None
                        ), ('fs_free', 253755392.0, None, None, 0, None),
                        (
                            'fs_used_percent', 8.159392789373815, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 276299776.0, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'rbd-rub.ec', {
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
                    0, 'Used: 3.44% - 19.4 TiB of 563 TiB', [
                        (
                            'fs_used', 20342374.399999976, 472614174.72,
                            531690946.56, 0, None
                        ), ('fs_free', 570425344.0, None, None, 0, None),
                        (
                            'fs_used_percent', 3.443379481718136, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 590767718.4, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'rub-s3.ec', {
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
                    0, 'Used: <0.01% - 4.88 KiB of 272 TiB', [
                        (
                            'fs_used', 0.004765629768371582, 228170137.6038125,
                            256691404.80428904, 0, None
                        ), ('fs_free', 285212672.0, None, None, 0, None),
                        (
                            'fs_used_percent', 1.6709039380592294e-09, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 285212672.0047656, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'scbench', {
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
                    0, 'Used: <0.01% - 2.32 GiB of 242 TiB', [
                        (
                            'fs_used', 2375.6800000071526, 203006214.14400002,
                            228381990.912, 0, None
                        ), ('fs_free', 253755392.0, None, None, 0, None),
                        (
                            'fs_used_percent', 0.0009361999129039439, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 253757767.68, None, None, 0, None)
                    ]
                )
            ]
        )
    ]
}
