#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.check_legacy_includes.network_fs import CHECK_DEFAULT_PARAMETERS

checkname = 'nfsmounts'

info = [
    ['/path/to/share1', 'hanging', '1611668', '794767', '712899', '32768'],
    ['/path/to/share2', 'ok', '-', '-', '-', '-'],
    ['/path/to/share3', 'drunk', '1611668', '794767', '712899', '32768'],
    ['/path/to/share4', 'ok', '1611668', '794767', '712899', '32768']
]

discovery = {
    '': [
        ('/path/to/share1', {}), ('/path/to/share2', {}),
        ('/path/to/share3', {}), ('/path/to/share4', {})
    ]
}

checks = {
    '': [
        ('/path/to/share1', CHECK_DEFAULT_PARAMETERS, [(2, 'Server not responding', [])]),
        ('/path/to/share2', CHECK_DEFAULT_PARAMETERS, [(0, 'Mount seems OK', [])]),
        ('/path/to/share3', CHECK_DEFAULT_PARAMETERS, [(2, 'Unknown state: drunk', [])]),
        (
            '/path/to/share4', CHECK_DEFAULT_PARAMETERS, [
                (0, '55.77% used (27.43 of 49.18 GB)', []),
            ],
        ),
        (
            '/path/to/share4',
            {
                **CHECK_DEFAULT_PARAMETERS,
                'has_perfdata': True,
            },
            [
                (0, '55.77% used (27.43 of 49.18 GB)', [
                    ('fs_used', 29450862592.0, 42248909619.2, 47530023321.6, 0.0, 52811137024.0),
                    ('fs_size', 52811137024.0, None, None, None, None),
                ]),
            ],
        ),
        (
            '/path/to/share4',
            {
                **CHECK_DEFAULT_PARAMETERS,
                'show_levels': 'on_magic',
                'magic': 0.3,
            },
            [
                (0, '55.77% used (27.43 of 49.18 GB)', []),
            ],
        ),
    ]
}
