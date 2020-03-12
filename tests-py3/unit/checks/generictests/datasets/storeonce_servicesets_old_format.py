#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'storeonce_servicesets'

freeze_time = '2020-01-02 13:41:00'

info = [
    ['[1]'], ['ServiceSet ID', '1'], ['ServiceSet Name', '', 'Service Set 1'],
    ['ServiceSet Alias', 'SET1'], ['Serial Number', 'CZ25132LTD01'],
    ['Software Version', '3.15.1-1636.1'],
    ['Product Class', 'HPE StoreOnce 4700 Backup'],
    ['Capacity in bytes', '75952808613643'],
    ['Free Space in bytes', '53819324528395'],
    ['User Data Stored in bytes', '305835970141743'],
    ['Size On Disk in bytes', '19180587585836'],
    ['Deduplication Ratio', '15.945078260668'],
    ['ServiceSet Health Level', '1'], ['ServiceSet Health', 'OK'],
    ['ServiceSet Status', 'Running'], ['Replication Health Level', '1'],
    ['Replication Health', 'OK'], ['Replication Status', 'Running'],
    ['Overall Health Level', '1'], ['Overall Health', 'OK'],
    ['Overall Status', 'Running'], ['Housekeeping Health Level', '1'],
    ['Housekeeping Health', 'OK'], ['Housekeeping Status', 'Running'],
    ['Primary Node', 'hpcz25132ltd'], ['Secondary Node', 'None'],
    ['Active Node', 'hpcz25132ltd']
]

discovery = {'': [('1', {})], 'capacity': [('1', {})]}

checks = {
    '': [
        (
            '1', {}, [
                (0, 'Alias: SET1', []),
                (0, 'Overall Status: Running, Overall Health: OK', [])
            ]
        )
    ],
    'capacity': [
        (
            '1', {}, [
                (
                    0, '29.14% used (10.07 of 34.54 PB)', [
                        (
                            'fs_used', 10807365276.0, 29669065864.704296,
                            33377699097.792336, 0, 37086332330.88037
                        ),
                        ('fs_size', 37086332330.88037, None, None, None, None)
                    ]
                ), (0, 'Dedup ratio: 15.95', [])
            ]
        )
    ]
}
