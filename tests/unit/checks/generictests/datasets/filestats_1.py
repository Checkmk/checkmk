#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'filestats'

info = [
    ["[[[file_stats aix agent files]]]"],
    [
        "{'stat_status': 'ok', 'age': 230276, 'mtime': 1544196317,"
        " 'path': '/home/mo/git/check_mk/agents/check_mk_agent.aix', 'type': 'file', 'size': 12886}"
    ],
    [
        "{'stat_status': 'ok', 'age': 18751603, 'mtime': 1525674990,"
        " 'path': '/home/mo/git/check_mk/agents/plugins/mk_sap.aix', 'type': 'file', 'size': 3928}"
    ],
    [
        "{'stat_status': 'ok', 'age': 230276, 'mtime': 1544196317, 'path':"
        " '/home/mo/git/check_mk/agents/plugins/mk_logwatch.aix', 'type': 'file', 'size': 1145}"
    ],
    [
        "{'stat_status': 'ok', 'age': 18751603, 'mtime': 1525674990, 'path':"
        " '/home/mo/git/check_mk/agents/plugins/netstat.aix', 'type': 'file', 'size': 1697}"
    ],
    [
        "{'stat_status': 'ok', 'age': 9398016, 'mtime': 1535028577, 'path':"
        " '/home/mo/git/check_mk/agents/plugins/mk_inventory.aix', 'type': 'file', 'size': 2637}"
    ],
    [
        "{'stat_status': 'ok', 'age': 18751603, 'mtime': 1525674990, 'path':"
        " '/home/mo/git/check_mk/agents/plugins/mk_db2.aix', 'type': 'file', 'size': 10138}"
    ],
    ["{'type': 'summary', 'count': 6}"],
    ['[[[count_only $ection with funny characters %s &! (count files in ~)]]]'],
    ["{'type': 'summary', 'count': 35819}"],
    ['[[[extremes_only log files]]]'],
    [
        "{'stat_status': 'ok', 'age': 89217820, 'mtime': 1455208773, 'path':"
        " '/var/log/installer/casper.log', 'type': 'file', 'size': 1216}"
    ],
    [
        "{'stat_status': 'ok', 'age': 4451, 'mtime': 1544422142, 'path': '/var/log/boot.log',"
        " 'type': 'file', 'size': 2513750}"
    ],
    [
        "{'stat_status': 'ok', 'age': 252, 'mtime': 1544426341, 'path': '/var/log/auth.log',"
        " 'type': 'file', 'size': 7288}"
    ],
    [
        "{'stat_status': 'ok', 'age': 15965608, 'mtime': 1528460985, 'path': '/var/log/tacwho.log',"
        " 'type': 'file', 'size': 0}"
    ],
    ["{'type': 'summary', 'count': 17}"],
    ['[[[single_file file1.txt]]]'],
    [
        "{'stat_status': 'ok', 'age': 52456, 'mtime': 1583771842, 'path': u'/home/file1.txt', 'type': 'file', 'size': 3804}"
    ],
    ['[[[single_file file2.txt]]]'],
    [
        "{'stat_status': 'ok', 'age': 52456, 'mtime': 1583771842, 'path': u'/home/file2.txt', 'type': 'file', 'size': 3804}"
    ],
    ['[[[single_file file3.txt]]]'],
    [
        "{'stat_status': 'ok', 'age': 52456, 'mtime': 1583771842, 'path': u'/home/file3.txt', 'type': 'file', 'size': 3804}"
    ],
    ['[[[single_file multiple-stats-per-single-service]]]'],
    [
        "{'stat_status': 'ok', 'age': 52456, 'mtime': 1583771842, 'path': u'/home/file3.txt', 'type': 'file', 'size': 3804}"],
    [    "{'stat_status': 'ok', 'age': 52456, 'mtime': 1583771842, 'path': u'/home/file3.txt', 'type': 'file', 'size': 3804}"
    ]
]

discovery = {
    '': [
        ('aix agent files', {}),
        ('$ection with funny characters %s &! (count files in ~)', {}),
        ('log files', {}),
    ],
    'single': [
    ('file1.txt', {}),
    ('file2.txt', {}),
    ('file3.txt', {}),
    ('multiple-stats-per-single-service', {}),
    ]
}

checks = {
    '': [
        ('aix agent files', {}, [(0, 'Files in total: 6', [('file_count', 6, None, None, None,
                                                            None)]), (0, 'Smallest: 1.12 kB', []),
                                 (0, 'Largest: 12.58 kB', []), (0, 'Newest: 2 days 15 hours', []),
                                 (0, 'Oldest: 217 days 0 hours', []),
                                 (0, '\n', [])]),
        ('aix agent files', {
            "maxsize_largest": (12 * 1024, 13 * 1024),
            "minage_newest": (3600 * 72, 3600 * 96)
        }, [(0, 'Files in total: 6', [('file_count', 6, None, None, None, None)]),
            (0, 'Smallest: 1.12 kB', []),
            (1, 'Largest: 12.58 kB (warn/crit at 12.00 kB/13.00 kB)', []),
            (2, 'Newest: 2 days 15 hours (warn/crit below 3 days 0 hours/4 days 0 hours)', []), (0, 'Oldest: 217 days 0 hours',
                                                                            []),
            (0, '\n', [])]),
        ('$ection with funny characters %s &! (count files in ~)', {
            "maxcount": (5, 10)
        }, [
            (2, 'Files in total: 35819 (warn/crit at 5/10)', [('file_count', 35819, 5, 10, None,
                                                               None)]),
        ]),
        ('log files', {}, [
            (0, 'Files in total: 17', [('file_count', 17, None, None, None, None)]),
            (0, 'Smallest: 0.00 B', []),
            (0, 'Largest: 2.40 MB', []),
            (0, 'Newest: 4 minutes 12 seconds', []),
            (0, 'Oldest: 2 years 302 days', []),
            (0, '\n', []),
        ]),
    ],
    'single': [
        ('file1.txt', {},
            [
                (0, 'Size: 3.71 kB', [('size', 3804)]),
                (0, 'Age: 14 hours 34 minutes', []),
            ]
            ),
        ('file2.txt',
            {
                'min_size': (2 * 1024, 1 * 1024),
                'max_size': (3 * 1024, 4 * 1024)
            },
            [
                (1, 'Size: 3.71 kB (warn/crit at 3.00 kB/4.00 kB)', [('size', 3804, 3072.0, 4096.0)]),
                (0, 'Age: 14 hours 34 minutes', []),
            ]
        ),
        ('file3.txt',
            {
                'min_age': (2 * 60, 1 * 60),
                'max_age': (3 * 60, 4 * 60)
            },
            [
                (0, 'Size: 3.71 kB', [('size', 3804)]),
                (2, 'Age: 14 hours 34 minutes (warn/crit at 3 minutes 0 seconds/4 minutes 0 seconds)', []),
            ]
        ),
        ('multiple-stats-per-single-service',
            {},
            [
                (1, 'Received multiple filestats per single file service. Please check agent plugin configuration (mk_filestats).', []),
                (0, 'Size: 3.71 kB', [('size', 3804)]),
                (0, 'Age: 14 hours 34 minutes', []),
            ]
        )
    ]

}
