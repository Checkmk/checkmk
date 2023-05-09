#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'filestats'

info = [
    ['[[[file_stats Filetransfer cofi-premium-world]]]'],
    [
        "{'stat_status': None, 'age': 76216, 'mtime': 1603481501, 'path': u'/opt/filetransfer/data/akb/paag01/cofi#ak/incoming/premium-world-check-day.xml', 'type': 'file', 'size': 9249108}"
    ],
    [
        "{'stat_status': None, 'age': 2025616, 'mtime': 1601532101, 'path': u'/opt/filetransfer/data/akb/paag01/cofi#ak/incoming/premium-world-check-month.xml', 'type': 'file', 'size': 271408990}"
    ],
    [
        "{'stat_status': None, 'age': 517260, 'mtime': 1603040457, 'path': u'/opt/filetransfer/data/akb/paag01/cofi#ak/incoming/premium-world-check-week.xml', 'type': 'file', 'size': 81099075}"
    ], ["{'count': 3, 'type': 'summary'}"]
]

discovery = {'single': [], '': [('Filetransfer cofi-premium-world', {})]}

checks = {
    '': [(
        'Filetransfer cofi-premium-world',
        {
            'show_all_files': True,
            'additional_rules': [
                ('DAY', '.*?/premium-world-check-day', {
                    'maxage_oldest': (1, 2)
                }),
                ('WEEK', '.*?/premium-world-check-week', {
                    'maxage_oldest': (3, 4)
                }),
                ('MONTH', '.*?/premium-world-check-month', {
                    'maxage_oldest': (5, 6)
                }),
            ]
        },
        [
            (0, 'Files in total: 3', [('file_count', 3, None, None, None, None)]),
            (0, 'Additional rules enabled', []),
            (0, '\nDAY', []),
            (0, 'Pattern: \'.*?/premium-world-check-day\'', []),
            (0, 'Files in total: 1', []),
            (0, 'Smallest: 8.82 MB', []),
            (0, 'Largest: 8.82 MB', []),
            (0, 'Newest: 21 h', []),
            (2, 'Oldest: 21 h (warn/crit at 1.00 s/2.00 s)', []),
            (0, '[/opt/filetransfer/data/akb/paag01/cofi#ak/incoming/premium-world-check-day.xml] Age: 21 h, Size: 8.82 MB(!!)', []),
            (0, '\nMONTH', []),
            (0, 'Pattern: \'.*?/premium-world-check-month\'', []),
            (0, 'Files in total: 1', []),
            (0, 'Smallest: 258.84 MB', []),
            (0, 'Largest: 258.84 MB', []),
            (0, 'Newest: 23 d', []),
            (2, 'Oldest: 23 d (warn/crit at 5.00 s/6.00 s)', []),
            (0, "[/opt/filetransfer/data/akb/paag01/cofi#ak/incoming/premium-world-check-month.xml] Age: 23 d, Size: 258.84 MB(!!)", []),
            (0, '\nWEEK', []),
            (0, 'Pattern: \'.*?/premium-world-check-week\'', []),
            (0, 'Files in total: 1', []),
            (0, 'Smallest: 77.34 MB', []),
            (0, 'Largest: 77.34 MB', []),
            (0, 'Newest: 6 d', []),
            (2, 'Oldest: 6 d (warn/crit at 3.00 s/4.00 s)', []),
            (0,  "[/opt/filetransfer/data/akb/paag01/cofi#ak/incoming/premium-world-check-week.xml] Age: 6 d, Size: 77.34 MB(!!)", []),
            (0, '\nRemaining files: 0', []),
            (0, '\n', []),
        ],
    )]
}
