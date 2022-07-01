#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'filestats'

info = [
    ['[[[file_stats dtb]]]'],
    [
        "{'stat_status': 'ok', 'age': 13761362, 'mtime': 1642827699, 'path': u'/var/bla', 'type': 'file', 'size': 47736}"
    ],
    [
        "{'stat_status': 'ok', 'age': 13592155, 'mtime': 1642996906, 'path': u'/var/foo', 'type': 'file', 'size': 18954}"
    ],
    [
        "{'stat_status': 'ok', 'age': 13505726, 'mtime': 1643083335, 'path': u'/var/boo', 'type': 'file', 'size': 38610}"
    ],
    ["{'count': 3, 'type': 'summary'}"],
]

discovery = {'single': [], '': [('dtb', {})]}

checks = {
    '': [(
        'dtb',
        {
            'maxcount': (1, 1),
            'show_all_files': True
        },
        [
            (2, 'Files in total: 3 (warn/crit at 1/1)\n[/var/bla]\n[/var/foo]\n[/var/boo]', [
                ('file_count', 3, 1.0, 1.0, None, None),
            ]),
            (0, 'Smallest: 18.51 kB', []),
            (0, 'Largest: 46.62 kB', []),
            (0, 'Newest: 156 d', []),
            (0, 'Oldest: 159 d', []),
            (0, '\n', []),
        ],
    ),]
}
