#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'storeonce_servicesets'

freeze_time = '2020-01-02 13:38:00'

info = [
    ['[1]'], ['ServiceSet ID', '1'], ['ServiceSet Name', 'Service Set 1'],
    ['ServiceSet Alias', 'SET1'], ['Serial Number', 'CZ25132LTD01'],
    ['Software Version', '3.18.7-1841.1'],
    ['Product Class', 'HPE StoreOnce 4700 Backup'],
    ['Deduplication Ratio', '16.626312639082'],
    ['ServiceSet Health Level', '1'], ['ServiceSet Health', 'OK'],
    ['ServiceSet Status', 'Running'], ['Replication Health Level', '1'],
    ['Replication Health', 'OK'], ['Replication Status', 'Running'],
    ['Overall Health Level', '1'], ['Overall Health', 'OK'],
    ['Overall Status', 'Running'], ['Housekeeping Health Level', '1'],
    ['Housekeeping Health', 'OK'], ['Housekeeping Status', 'Running'],
    ['Primary Node', 'hpcz25132ltd'], ['Secondary Node', 'None'],
    ['Active Node', 'hpcz25132ltd'], ['cloudCapacityBytes', '0'],
    ['cloudDiskBytes', '0'], ['cloudReadWriteLicensedDiskBytes', '0'],
    ['cloudFreeBytes', '0'], ['cloudUserBytes', '0'],
    ['localCapacityBytes', '75952808613643'],
    ['localDiskBytes', '49547481098312'], ['localFreeBytes', '21647101662987'],
    ['localUserBytes', '823791911219548'],
    ['combinedCapacityBytes', '75952808613643'],
    ['combinedDiskBytes', '49547481098312'],
    ['combinedFreeBytes', '21647101662987'],
    ['combinedUserBytes', '823791911219548']
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
                    0, '71.50% used (49.4 of 69.1 TiB)', [
                        (
                            'fs_used', 51789957.953125, 57947394.26700058,
                            65190818.550375655, 0, 72434242.83375072
                        ),
                        ('fs_size', 72434242.83375072, None, None, None, None),
                        (
                            'fs_used_percent', 71.49927427555504, None, None,
                            None, None
                        )
                    ]
                ), (0, 'Total local: 69.1 TiB', []),
                (0, 'Free local: 19.7 TiB', []),
                (
                    0, 'Dedup ratio: 16.63',
                    [('dedup_rate', 16.626312639082, None, None, None, None)]
                )
            ]
        )
    ]
}
