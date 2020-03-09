#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'ceph_df'

info = [
    [u'GLOBAL:'],
    [u'SIZE', u'AVAIL', u'RAW', u'USED', u'%RAW', u'USED', u'OBJECTS'],
    [u'253', u'GiB', u'245', u'GiB', u'7.8', u'GiB', u'3.10', u'839'],
    [u'POOLS:'],
    [
        u'NAME', u'ID', u'QUOTA', u'OBJECTS', u'QUOTA', u'BYTES', u'USED',
        u'%USED', u'MAX', u'AVAIL', u'OBJECTS', u'DIRTY', u'READ', u'WRITE',
        u'RAW', u'USED'
    ],
    [
        u'cephfs_data', u'1', u'N/A', u'N/A', u'1.6', u'GiB', u'1.97', u'77',
        u'GiB', u'809', u'809', u'33', u'B', u'177', u'KiB', u'4.7', u'GiB'
    ],
    [
        u'cephfs_metadata', u'2', u'N/A', u'N/A', u'32', u'MiB', u'0.04',
        u'77', u'GiB', u'30', u'30', u'407', u'B', u'14', u'KiB', u'95', u'MiB'
    ]
]

discovery = {
    '': [('SUMMARY', {}), (u'cephfs_data', {}), (u'cephfs_metadata', {})]
}

checks = {
    '': [
        (
            'SUMMARY', {
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
                    0, '3.16% used (8.00 of 253.00 GB)', [
                        ('SUMMARY', 8192.0, 207257.6, 233164.8, 0, 259072.0),
                        ('fs_size', 259072.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'cephfs_data', {
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
                    0, '2.04% used (1.60 of 78.60 GB)', [
                        (
                            u'cephfs_data', 1638.3999999999942, 64389.12,
                            72437.76, 0, 80486.4
                        ), ('fs_size', 80486.4, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'cephfs_metadata', {
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
                    0, '0.04% used (32.00 MB of 77.03 GB)', [
                        (
                            u'cephfs_metadata', 32.0, 63104.0, 70992.0, 0,
                            78880.0
                        ), ('fs_size', 78880.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
