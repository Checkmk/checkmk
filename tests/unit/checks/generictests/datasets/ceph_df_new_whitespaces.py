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
    ['253', 'GiB', '245', 'GiB', '7.8', 'GiB', '3.10', '839'], ['POOLS:'],
    [
        'NAME', 'ID', 'QUOTA', 'OBJECTS', 'QUOTA', 'BYTES', 'USED', '%USED',
        'MAX', 'AVAIL', 'OBJECTS', 'DIRTY', 'READ', 'WRITE', 'RAW', 'USED'
    ],
    [
        'cephfs_data', '1', 'N/A', 'N/A', '1.6', 'GiB', '1.97', '77', 'GiB',
        '809', '809', '33', 'B', '177', 'KiB', '4.7', 'GiB'
    ],
    [
        'cephfs_metadata', '2', 'N/A', 'N/A', '32', 'MiB', '0.04', '77', 'GiB',
        '30', '30', '407', 'B', '14', 'KiB', '95', 'MiB'
    ]
]

discovery = {
    '': [('SUMMARY', {}), ('cephfs_data', {}), ('cephfs_metadata', {})]
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
                    0, '3.16% used (8.00 of 253 GiB)', [
                        ('fs_used', 8192.0, 207257.6, 233164.8, 0, 259072.0),
                        ('fs_size', 259072.0, None, None, None, None),
                        (
                            'fs_used_percent', 3.1620553359683794, None, None,
                            None, None
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
                    0, '2.04% used (1.60 of 78.6 GiB)', [
                        (
                            'fs_used', 1638.3999999999942, 64389.12, 72437.76,
                            0, 80486.4
                        ), ('fs_size', 80486.4, None, None, None, None),
                        (
                            'fs_used_percent', 2.035623409669204, None, None,
                            None, None
                        )
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
                    0, '0.04% used (32.0 MiB of 77.0 GiB)', [
                        ('fs_used', 32.0, 63104.0, 70992.0, 0, 78880.0),
                        ('fs_size', 78880.0, None, None, None, None),
                        (
                            'fs_used_percent', 0.04056795131845842, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
