#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
from cmk.base.plugins.agent_based.df_section import parse_df

checkname = 'df'

parsed = parse_df([
    ['C:\\\\', 'NTFS', '62553084', '16898384', '45654700', '28%', 'C:\\\\'],
    ['SQL_Database_[GROUPME]', 'NTFS', '10450940', '2932348', '7518592', '29%', 'D:\\\\'],
    ['Scratch_Volume_[GROUPME]', 'NTFS', '5208060', '791864', '4416196', '16%', 'E:\\\\'],
])

discovery = {
    '': [
        (
            'C:\\\\ C://',
            {
                'include_volume_name': True
            },
        ),
        (
            'SQL_Database_[GROUPME] D://',
            {
                'include_volume_name': True
            },
        ),
        (
            'Scratch_Volume_[GROUPME] E://',
            {
                'include_volume_name': True
            },
        ),
    ],
}

checks = {
    '': [
        (
            'C:\\\\ C://',
            {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False,
                'include_volume_name': True
            },
            [
                (
                    0,
                    '27.01% used (16.12 of 59.66 GB)',
                    [
                        ('fs_used', 16502.328125, 48869.596875, 54978.296484375, 0, 61086.99609375),
                        ('fs_size', 61086.99609375, None, None, None, None),
                        ('fs_used_percent', 27.014469822143383, None, None, None, None),
                    ],
                ),
            ],
        ),
        (
            'SQL_Database_[GROUPME] D://',
            {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False,
                'include_volume_name': True
            },
            [
                (
                    0,
                    '28.06% used (2.80 of 9.97 GB)',
                    [
                        ('fs_used', 2863.62109375, 8164.796875, 9185.396484375, 0, 10205.99609375),
                        ('fs_size', 10205.99609375, None, None, None, None),
                        ('fs_used_percent', 28.058222513955684, None, None, None, None),
                    ],
                ),
            ],
        ),
        (
            'Scratch_Volume_[GROUPME] E://',
            {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False,
                'include_volume_name': True
            },
            [
                (
                    0,
                    '15.2% used (773.30 MB of 4.97 GB)',
                    [
                        ('fs_used', 773.3046875, 4068.796875, 4577.396484375, 0, 5085.99609375),
                        ('fs_size', 5085.99609375, None, None, None, None),
                        ('fs_used_percent', 15.204586736711942, None, None, None, None),
                    ],
                ),
            ],
        ),
    ],
}

mock_host_conf = {'': [[('myGroup', 'GROUPME')]]}  # old-style rule spec

mock_host_conf_merged = {'': {'include_volume_name': True}}
