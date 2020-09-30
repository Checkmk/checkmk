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
                [('/var/log/sys*', {
                    'maxsize_largest': (1, 2)
                })],
                'show_all_files': True,
            }, [
                (
                    0, 'Files in total: 5', [
                        ('file_count', 5, None, None, None, None)
                    ]
                ),
                (0, 'Smallest: 479.00 B', []),
                (2, 'Largest: 138.57 kB (warn/crit at 4.00 B/5.00 B)', []),
                (0, 'Newest: 356 m', []),
                (0, 'Oldest: 53 d', []),
                (0, "Files matching '/var/log/sys*': 3", []),
                (0, 'Smallest: 5.07 MB', []),
                (2, 'Largest: 21.10 MB (warn/crit at 1.00 B/2.00 B)', []),
                (0, 'Newest: 0.00 s', []),
                (0, 'Oldest: 47 d', []),
                (0, '\nFiles matching \'/var/log/sys*\':\n', []),
                (0, '[/var/log/syslog] Age: 0.00 s, Size: 13.23 MB(!!)\n[/var/log/syslog.1] Age: 19 d, Size: 21.10 MB(!!)\n[/var/log/syslog.3.gz] Age: 47 d, Size: 5.07 MB(!!)', []),
                (0, '\n(Remaining) files in file group:\n[/var/log/apport.log.2.gz] Age: 53 d, Size: 479.00 B(!!)\n[/var/log/boot.log] Age: 356 m, Size: 138.57 kB(!!)', []),
            ]
        ),
    ]
}
