#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
from cmk.base.plugins.agent_based.df_section import parse_df

checkname = 'df'

parsed = parse_df([
    ['C:\\', 'NTFS', '8192620', '7724268', '468352', '95%', 'C:\\'],
    ['New_Volume', 'NTFS', '10240796', '186256', '10054540', '2%', 'E:\\'],
    ['New_Volume', 'NTFS', '124929596', '50840432', '74089164', '41%', 'F:\\'],
])

discovery = {
    '': [
        (
            'C:/',
            {
                "item_appearance": "mountpoint",
                "mountpoint_for_block_devices": "volume_name",
            },
        ),
        (
            'E:/',
            {
                "item_appearance": "mountpoint",
                "mountpoint_for_block_devices": "volume_name",
            },
        ),
        (
            'F:/',
            {
                "item_appearance": "mountpoint",
                "mountpoint_for_block_devices": "volume_name",
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
                'Used: 94.28% - 7.37 GiB of 7.81 GiB (warn/crit at 80.00%/90.00% used)',
                [
                    ('fs_used', 7543.23046875, 6400.484375, 7200.544921875, 0, None),
                    ('fs_free', 457.375, None, None, 0, None),
                    ('fs_used_percent', 94.28324516455054, 80.0, 90.0, 0.0, 100.0),
                    ('fs_size', 8000.60546875, None, None, 0, None),
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
            (0, 'Used: 1.82% - 182 MiB of 9.77 GiB', [
                ('fs_used', 181.890625, 8000.621875, 9000.699609375, 0, None),
                ('fs_free', 9818.88671875, None, None, 0, None),
                ('fs_used_percent', 1.8187648694496015, 80.0, 90.0, 0.0, 100.0),
                ('fs_size', 10000.77734375, None, None, 0, None),
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
                'Used: 1.82% - 182 MiB of 9.77 GiB',
                [
                    ('fs_used', 181.890625, 8000.621875, 9000.699609375, 0, None),
                    ('fs_free', 9818.88671875, None, None, 0, None),
                    ('fs_used_percent', 1.8187648694496015, 80.0, 90.0, 0.0, 100.0),
                    ('fs_size', 10000.77734375, None, None, 0, None),
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
                'Used: 40.70% - 48.5 GiB of 119 GiB',
                [
                    ('fs_used', 49648.859375, 97601.246875, 109801.402734375, 0, None),
                    ('fs_free', 72352.69921875, None, None, 0, None),
                    ('fs_used_percent', 40.695266476327994, 80.0, 90.0, 0.0, 100.0),
                    ('fs_size', 122001.55859375, None, None, 0, None),
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
        }, [
            (
                2,
                'Used: 94.28% - 7.37 GiB of 7.81 GiB (warn/crit at 80.00%/90.00% used)',
                [
                    ('fs_used', 7543.23046875, 6400.484375, 7200.544921875, 0, None),
                    ('fs_free', 457.375, None, None, 0, None),
                    ('fs_used_percent', 94.28324516455054, 80.0, 90.0, 0.0, 100.0),
                    ('fs_size', 8000.60546875, None, None, 0, None),
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
        }, [
            (
                0,
                'Used: 1.82% - 182 MiB of 9.77 GiB',
                [
                    ('fs_used', 181.890625, 8000.621875, 9000.699609375, 0, None),
                    ('fs_free', 9818.88671875, None, None, 0, None),
                    ('fs_used_percent', 1.8187648694496015, 80.0, 90.0, 0.0, 100.0),
                    ('fs_size', 10000.77734375, None, None, 0, None),
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
        }, [
            (
                0,
                'Used: 40.70% - 48.5 GiB of 119 GiB',
                [
                    ('fs_used', 49648.859375, 97601.246875, 109801.402734375, 0, None),
                    ('fs_free', 72352.69921875, None, None, 0, None),
                    ('fs_used_percent', 40.695266476327994, 80.0, 90.0, 0.0, 100.0),
                    ('fs_size', 122001.55859375, None, None, 0, None),
                ],
            ),
        ]),
    ]
}
