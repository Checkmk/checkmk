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
    ['200T', '186T', '13808G', '6.74', '8774k'], ['POOLS:'],
    [
        'NAME', 'ID', 'CATEGORY', 'QUOTA', 'OBJECTS', 'QUOTA', 'BYTES', 'USED',
        '%USED', 'MAX', 'AVAIL', 'OBJECTS', 'DIRTY', 'READ', 'WRITE', 'RAW',
        'USED'
    ],
    [
        'seafile-commits', '33', '-', 'N/A', 'N/A', '276M', '0.04', '744G',
        '506506', '494k', '315k', '496k', '829M'
    ],
    [
        'seafile-blocks', '35', '-', 'N/A', 'N/A', '685G', '0.56', '119T',
        '879162', '858k', '891k', '1168k', '1027G'
    ],
    [
        'seafile-fs', '36', '-', 'N/A', 'N/A', '11412M', '1.47', '744G',
        '2502095', '2443k', '5782k', '2660k', '34237M'
    ],
    [
        'seafile-blocks-cache', '37', '-', 'N/A', '200G', '149G', '16.69',
        '744G', '198252', '96433', '5105k', '1944k', '447G'
    ],
    [
        'rbd', '49', '-', 'N/A', 'N/A', '3106G', '2.47', '119T', '795700',
        '777k', '16212k', '14942k', '4660G'
    ],
    [
        'rbd-cache', '50', '-', 'N/A', 'N/A', '40652M', '5.06', '744G',
        '10173', '3565', '50513k', '558M', '119G'
    ],
    [
        'cephfs01_meta', '53', '-', 'N/A', 'N/A', '131M', '0.02', '744G',
        '24170', '24170', '30172', '14199k', '393M'
    ],
    [
        'cephfs01', '54', '-', 'N/A', 'N/A', '4643G', '3.65', '119T',
        '4046530', '3951k', '72301', '4396k', '6965G'
    ],
    [
        'cephfs01-cache', '55', '-', 'N/A', 'N/A', '81681M', '9.67', '744G',
        '22523', '11189', '86325', '16059k', '239G'
    ]
]

discovery = {
    '': [
        ('SUMMARY', {}), ('cephfs01', {}), ('cephfs01-cache', {}),
        ('cephfs01_meta', {}), ('rbd', {}), ('rbd-cache', {}),
        ('seafile-blocks', {}), ('seafile-blocks-cache', {}),
        ('seafile-commits', {}), ('seafile-fs', {})
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
                    0, '7.00% used (14.0 of 200 TiB)', [
                        (
                            'fs_used', 14680064.0, 167772160.0, 188743680.0, 0,
                            209715200.0
                        ), ('fs_size', 209715200.0, None, None, None, None),
                        ('fs_used_percent', 7.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'cephfs01', {
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
                    0, '3.67% used (4.53 of 124 TiB)', [
                        (
                            'fs_used', 4754432.0, 103627980.8, 116581478.4, 0,
                            129534976.0
                        ), ('fs_size', 129534976.0, None, None, None, None),
                        (
                            'fs_used_percent', 3.6703847461244754, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'cephfs01-cache', {
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
                    0, '9.68% used (79.8 of 824 GiB)', [
                        ('fs_used', 81681.0, 674829.6, 759183.3, 0, 843537.0),
                        ('fs_size', 843537.0, None, None, None, None),
                        (
                            'fs_used_percent', 9.683155569939434, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'cephfs01_meta', {
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
                    0, '0.02% used (131 MiB of 744 GiB)', [
                        ('fs_used', 131.0, 609589.6, 685788.3, 0, 761987.0),
                        ('fs_size', 761987.0, None, None, None, None),
                        (
                            'fs_used_percent', 0.01719189434990361, None, None,
                            None, None
                        )
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
                    0, '2.49% used (3.03 of 122 TiB)', [
                        (
                            'fs_used', 3180544.0, 102368870.4, 115164979.2, 0,
                            127961088.0
                        ), ('fs_size', 127961088.0, None, None, None, None),
                        (
                            'fs_used_percent', 2.485555608905107, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'rbd-cache', {
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
                    0, '5.07% used (39.7 of 784 GiB)', [
                        ('fs_used', 40652.0, 642006.4, 722257.2, 0, 802508.0),
                        ('fs_size', 802508.0, None, None, None, None),
                        (
                            'fs_used_percent', 5.065619283546083, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'seafile-blocks', {
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
                    0, '0.56% used (685 GiB of 120 TiB)', [
                        (
                            'fs_used', 701440.0, 100385587.2, 112933785.6, 0,
                            125481984.0
                        ), ('fs_size', 125481984.0, None, None, None, None),
                        (
                            'fs_used_percent', 0.5589965807362434, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'seafile-blocks-cache', {
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
                    0, '16.69% used (149 of 893 GiB)', [
                        ('fs_used', 152576.0, 731545.6, 822988.8, 0, 914432.0),
                        ('fs_size', 914432.0, None, None, None, None),
                        (
                            'fs_used_percent', 16.685330347144458, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'seafile-commits', {
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
                    0, '0.04% used (276 MiB of 744 GiB)', [
                        ('fs_used', 276.0, 609705.6, 685918.8, 0, 762132.0),
                        ('fs_size', 762132.0, None, None, None, None),
                        (
                            'fs_used_percent', 0.036214199115113914, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            'seafile-fs', {
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
                    0, '1.48% used (11.1 of 755 GiB)', [
                        ('fs_used', 11412.0, 618614.4, 695941.2, 0, 773268.0),
                        ('fs_size', 773268.0, None, None, None, None),
                        (
                            'fs_used_percent', 1.4758143360387344, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
