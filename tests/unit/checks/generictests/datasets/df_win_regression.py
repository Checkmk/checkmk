#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'df'

info = [
    ['C:\\', 'NTFS', '8192620', '7724268', '468352', '95%', 'C:\\'],
    ['New_Volume', 'NTFS', '10240796', '186256', '10054540', '2%', 'E:\\'],
    ['New_Volume', 'NTFS', '124929596', '50840432', '74089164', '41%', 'F:\\'],
]

discovery = {
    '': [
        (
            'C:/',
            {
                'include_volume_name': False
            },
        ),
        (
            'E:/',
            {
                'include_volume_name': False
            },
        ),
        (
            'F:/',
            {
                'include_volume_name': False
            },
        ),
    ]
}

checks = {
    '': [
        ('C:/', {
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
                '94.28% used (7.37 of 7.81 GB, warn/crit at 80.0%/90.0%)',
                [
                    ('fs_used', 7543.23046875, 6400.484375, 7200.544921875, 0, 8000.60546875),
                    ('fs_size', 8000.60546875, None, None, None, None),
                    ('fs_used_percent', 94.28324516455054, None, None, None, None),
                ],
            ),
        ]),
        ('New_Volume E:/', {
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
            (0, '1.82% used (181.89 MB of 9.77 GB)', [
                ('fs_used', 181.890625, 8000.621875, 9000.699609375, 0, 10000.77734375),
                ('fs_size', 10000.77734375, None, None, None, None),
                ('fs_used_percent', 1.8187648694496015, None, None, None, None),
            ]),
        ]),
        ('E:/', {
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
                0,
                '1.82% used (181.89 MB of 9.77 GB)',
                [
                    ('fs_used', 181.890625, 8000.621875, 9000.699609375, 0, 10000.77734375),
                    ('fs_size', 10000.77734375, None, None, None, None),
                    ('fs_used_percent', 1.8187648694496015, None, None, None, None),
                ],
            ),
        ]),
        ('F:/', {
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
                0,
                '40.7% used (48.49 of 119.14 GB)',
                [
                    ('fs_used', 49648.859375, 97601.246875, 109801.402734375, 0, 122001.55859375),
                    ('fs_size', 122001.55859375, None, None, None, None),
                    ('fs_used_percent', 40.695266476327994, None, None, None, None),
                ],
            ),
        ]),
        ('C:/', {
            'levels': (80.0, 90.0),
            'magic_normsize': 20,
            'levels_low': (50.0, 60.0),
            'trend_range': 24,
            'trend_perfdata': True,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'show_inodes': 'onlow',
            'show_reserved': False,
            'include_volume_name': False
        }, [
            (
                2,
                '94.28% used (7.37 of 7.81 GB, warn/crit at 80.0%/90.0%)',
                [
                    ('fs_used', 7543.23046875, 6400.484375, 7200.544921875, 0, 8000.60546875),
                    ('fs_size', 8000.60546875, None, None, None, None),
                    ('fs_used_percent', 94.28324516455054, None, None, None, None),
                ],
            ),
        ]),
        ('E:/', {
            'levels': (80.0, 90.0),
            'magic_normsize': 20,
            'levels_low': (50.0, 60.0),
            'trend_range': 24,
            'trend_perfdata': True,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'show_inodes': 'onlow',
            'show_reserved': False,
            'include_volume_name': False
        }, [
            (
                0,
                '1.82% used (181.89 MB of 9.77 GB)',
                [
                    ('fs_used', 181.890625, 8000.621875, 9000.699609375, 0, 10000.77734375),
                    ('fs_size', 10000.77734375, None, None, None, None),
                    ('fs_used_percent', 1.8187648694496015, None, None, None, None),
                ],
            ),
        ]),
        ('F:/', {
            'levels': (80.0, 90.0),
            'magic_normsize': 20,
            'levels_low': (50.0, 60.0),
            'trend_range': 24,
            'trend_perfdata': True,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'show_inodes': 'onlow',
            'show_reserved': False,
            'include_volume_name': False
        }, [
            (
                0,
                '40.7% used (48.49 of 119.14 GB)',
                [
                    ('fs_used', 49648.859375, 97601.246875, 109801.402734375, 0, 122001.55859375),
                    ('fs_size', 122001.55859375, None, None, None, None),
                    ('fs_used_percent', 40.695266476327994, None, None, None, None),
                ],
            ),
        ]),
    ]
}
