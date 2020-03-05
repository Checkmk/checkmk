#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'df'

info = [
    [
        u'/dev/sda4', u'ext4', u'143786696', u'101645524', u'34814148', u'75%',
        u'/'
    ],
    [u'/dev/sda2', u'ext4', u'721392', u'151120', u'517808', u'23%', u'/boot'],
    [u'[df_inodes_start]'],
    [u'/dev/sda4', u'ext4', u'9142272', u'1654272', u'7488000', u'19%', u'/'],
    [u'/dev/sda2', u'ext4', u'46848', u'304', u'46544', u'1%', u'/boot'],
    [u'[df_inodes_end]']
]

discovery = {'': [(u'/', {"include_volume_name": False}), (u'/boot', {"include_volume_name": False})]}

checks = {
    '': [
        (
            u'/', {
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
                    0, '75.79% used (103.92 of 137.13 GB)', [
                        (
                            u'/', 106418.50390625, 112333.35625,
                            126375.02578125, 0, 140416.6953125
                        ), ('fs_size', 140416.6953125, None, None, None, None),
                        (
                            'inodes_used', 1654272, 8228044.8, 8685158.4, 0.0,
                            9142272.0
                        )
                    ]
                )
            ]
        ),
        (
            u'/dev/sda4 /', {
                'show_inodes': 'onlow',
                'inodes_levels': (10.0, 5.0),
                'trend_range': 24,
                'show_reserved': False,
                'show_levels': 'onmagic',
                'trend_perfdata': True,
                'levels_low': (50.0, 60.0),
                'levels': (80.0, 90.0),
                'magic_normsize': 20
            }, [
                (
                    0, '75.79% used (103.92 of 137.13 GB)', [
                        (
                            u'/', 106418.50390625, 112333.35625,
                            126375.02578125, 0, 140416.6953125
                        ), ('fs_size', 140416.6953125, None, None, None, None),
                        (
                            'inodes_used', 1654272, 8228044.8, 8685158.4, 0.0,
                            9142272.0
                        )
                    ]
                )
            ]
        ),
        (
            u'/dev/sda4 /', {
                'show_inodes': 'onlow',
                'subtract_reserved': True,
                'inodes_levels': (10.0, 5.0),
                'trend_range': 24,
                'show_reserved': True,
                'show_levels': 'onmagic',
                'trend_perfdata': True,
                'levels_low': (50.0, 60.0),
                'levels': (80.0, 90.0),
                'magic_normsize': 20
            }, [
                (
                    0,
                    '74.49% used (96.94 of 130.14 GB), additionally reserved for root: 6.99 GB',
                    [
                        (
                            u'/', 99263.20703125, 112333.35625,
                            126375.02578125, 0, 140416.6953125
                        ), ('fs_size', 140416.6953125, None, None, None, None),
                        (
                            'fs_free', 33998.19140625, None, None, 0,
                            140416.6953125
                        ), ('reserved', 7155.296875, None, None, None, None),
                        (
                            'inodes_used', 1654272, 8228044.8, 8685158.4, 0.0,
                            9142272.0
                        )
                    ]
                )
            ]
        ),
        (
            u'/', {
                'show_inodes': 'onlow',
                'inodes_levels': (10.0, 5.0),
                'trend_range': 24,
                'show_reserved': True,
                'show_levels': 'onmagic',
                'trend_perfdata': True,
                'levels_low': (50.0, 60.0),
                'levels': (80.0, 90.0),
                'magic_normsize': 20
            }, [
                (
                    0,
                    '75.79% used (103.92 of 137.13 GB), therein reserved for root: 5.1% (6.99 GB)',
                    [
                        (
                            u'/', 106418.50390625, 112333.35625,
                            126375.02578125, 0, 140416.6953125
                        ), ('fs_size', 140416.6953125, None, None, None, None),
                        ('reserved', 7155.296875, None, None, None, None),
                        (
                            'inodes_used', 1654272, 8228044.8, 8685158.4, 0.0,
                            9142272.0
                        )
                    ]
                )
            ]
        ),
        (
            u'/dev/sda4 /', {
                'show_inodes': 'onlow',
                'inodes_levels': (10.0, 5.0),
                'trend_range': 24,
                'show_reserved': True,
                'show_levels': 'onmagic',
                'trend_perfdata': True,
                'levels_low': (50.0, 60.0),
                'levels': (80.0, 90.0),
                'magic_normsize': 20
            }, [
                (
                    0,
                    '75.79% used (103.92 of 137.13 GB), therein reserved for root: 5.1% (6.99 GB)',
                    [
                        (
                            u'/', 106418.50390625, 112333.35625,
                            126375.02578125, 0, 140416.6953125
                        ), ('fs_size', 140416.6953125, None, None, None, None),
                        ('reserved', 7155.296875, None, None, None, None),
                        (
                            'inodes_used', 1654272, 8228044.8, 8685158.4, 0.0,
                            9142272.0
                        )
                    ]
                )
            ]
        ),
        (
            u'/home', {
                'show_inodes': 'onlow',
                'inodes_levels': (10.0, 5.0),
                'trend_range': 24,
                'show_reserved': False,
                'show_levels': 'onmagic',
                'trend_perfdata': True,
                'levels_low': (50.0, 60.0),
                'levels': (80.0, 90.0),
                'magic_normsize': 20
            }, []
        ),
        (
            u'/', {
                'show_inodes': 'onlow',
                'inodes_levels': (90.0, 5.0)
            }, [
                (
                    1,
                    u'75.79% used (103.92 of 137.13 GB), Inodes Used: 18.09% (warn/crit at 10.0%/95.0%), inodes available: 7.49 M/81.91%',
                    [
                        (
                            u'/', 106418.50390625, 112333.35625,
                            126375.02578125, 0, 140416.6953125
                        ), ('fs_size', 140416.6953125, None, None, None, None),
                        (
                            'inodes_used', 1654272, 914227.2000000001,
                            8685158.4, 0.0, 9142272.0
                        )
                    ]
                )
            ]
        ),
        (
            u'/', {
                'show_inodes': 'onlow',
                'inodes_levels': (8542272, 8142272)
            }, [
                (
                    2,
                    u'75.79% used (103.92 of 137.13 GB), Inodes Used: 1.65 M (warn/crit at 600.00 k/1.00 M), inodes available: 7.49 M/81.91%',
                    [
                        (
                            u'/', 106418.50390625, 112333.35625,
                            126375.02578125, 0, 140416.6953125
                        ), ('fs_size', 140416.6953125, None, None, None, None),
                        (
                            'inodes_used', 1654272, 600000.0, 1000000.0, 0.0,
                            9142272.0
                        )
                    ]
                )
            ]
        ),
        (
            u'all', {
                'patterns': ['*']
            }, [
                (
                    0, '75.55% used (104.12 of 137.81 GB) (2 filesystems)', [
                        (
                            u'all', 106617.31640625, 112896.94375,
                            127009.06171875, 0, 141121.1796875
                        ), ('fs_size', 141121.1796875, None, None, None, None),
                        ('inodes_used', 1654576, None, None, 0.0, 9189120.0)
                    ]
                )
            ]
        ),
        (
            u'parts', {
                'patterns': ['*oot', '/']
            }, [
                (
                    0, '75.55% used (104.12 of 137.81 GB) (2 filesystems)', [
                        (
                            u'parts', 106617.31640625, 112896.94375,
                            127009.06171875, 0, 141121.1796875
                        ), ('fs_size', 141121.1796875, None, None, None, None),
                        ('inodes_used', 1654576, None, None, 0.0, 9189120.0)
                    ]
                )
            ]
        ),
        (
            u'/boot', {
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
                    0, '28.22% used (198.81 of 704.48 MB)', [
                        (
                            u'/boot', 198.8125, 563.5875, 634.0359375, 0,
                            704.484375
                        ), ('fs_size', 704.484375, None, None, None, None),
                        (
                            'inodes_used', 304, 42163.200000000004, 44505.6,
                            0.0, 46848.0
                        )
                    ]
                )
            ]
        )
    ]
}
