#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'filestats'

info = [
    ['[[[file_stats foo]]]'],
    [
        "{'age': 21374, 'mtime': 1600757875, 'path': '/var/log/boot.log', 'size': 141894, 'stat_status': 'ok', 'type': 'file'}"
    ],
    [
        "{'stat_status': 'ok', 'age': 0, 'mtime': 160779533, 'path': '/var/log/syslog', 'type': 'file', 'size': 13874994}"
    ],
    [
        "{'stat_status': 'ok', 'age': 4079566, 'mtime': 1596699967, 'path': '/var/log/syslog.3.gz', 'type': 'file', 'size': 5313033}"
    ],
    [
        "{'stat_status': 'ok', 'age': 1661230, 'mtime': 1599118303, 'path': '/var/log/syslog.1', 'type': 'file', 'size': 22121937}"
    ],
    [
        "{'stat_status': 'ok', 'age': 4583773, 'mtime': 1596195760, 'path': '/var/log/apport.log.2.gz', 'type': 'file', 'size': 479}"
    ], ["{'type': 'summary', 'count': 5}"]
]

discovery = {'': [('foo', {})], 'single': []}

checks = {
    '': [
        (
            'foo', {
                'maxsize_largest': (4, 5),
                'additional_rules':
                [('Sys-related files', '/var/log/sys*', {
                    'maxsize_largest': (1, 2)
                }),
                ('', '/var/log/app*', {
                    'maxsize_largest': (100, 200)
                })],
                'show_all_files': True,
            }, [
                (
                    0, 'Files in total: 5', [
                        ('file_count', 5, None, None, None, None)
                    ]
                ),
                (0, 'Smallest: 139 KiB', []),
                (2, 'Largest: 139 KiB (warn/crit at 4 B/5 B)', []),
                (0, 'Newest: 5 hours 56 minutes', []),
                (0, 'Oldest: 5 hours 56 minutes', []),
                (0, 'Additional rules enabled', []),
                (0, '\nSys-related files', []),
                (0, "Pattern: '/var/log/sys*'", []),
                (0, 'Files in total: 3', []),
                (0, 'Smallest: 5.07 MiB', []),
                (2, 'Largest: 21.1 MiB (warn/crit at 1 B/2 B)', []),
                (0, 'Newest: 0 seconds', []),
                (0, 'Oldest: 47 days 5 hours', []),
                (0, '[/var/log/syslog] Age: 0 seconds, Size: 13.2 MiB(!!)\n[/var/log/syslog.1] Age: 19 days 5 hours, Size: 21.1 MiB(!!)\n[/var/log/syslog.3.gz] Age: 47 days 5 hours, Size: 5.07 MiB(!!)', []),
                (0, '\n', []),
                (0, "Pattern: '/var/log/app*'", []),
                (0, 'Files in total: 1', []),
                (0, 'Smallest: 479 B', []),
                (2, 'Largest: 479 B (warn/crit at 100 B/200 B)', []),
                (0, 'Newest: 53 days 1 hour', []),
                (0, 'Oldest: 53 days 1 hour', []),
                (0, '[/var/log/apport.log.2.gz] Age: 53 days 1 hour, Size: 479 B(!!)', []),
                (0, '\nRemaining files: 1', []),
                (0, '\n[/var/log/boot.log] Age: 5 hours 56 minutes, Size: 139 KiB(!!)', []),
            ]
        ),
    ]
}
