#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'fileinfo'

info = [
    ['1563288717'], ['[[[header]]]'], ['name', 'status', 'size', 'time'],
    ['[[[content]]]'],
    ['/gw/ro-gr/do/wpgate/gwia/dsnhold/5753717f.000', 'ok', 384, 1465079135],
    ['/gw/ro-gr/do/wpgate/gwia/dsnhold/5753f6e9.000', 'ok', 384, 1465113289],
    ['/gw/ro-gr/do/wpgate/gwia/dsnhold/5754104f.000', 'ok', 384, 1465119791],
    ['/gw/ro-gr/do/wpgate/gwia/dsnhold/57543199.000', 'ok', 384, 1465128313]
]

discovery = {
    '': [],
    'groups': [
        (
            'random_files', {
                'group_patterns': [('/gw/ro-gr/do/wpgate/gwia/dsnhold*', '')]
            }
        ),
        (
            'random_files', {
                'group_patterns': [('/gw/ro-gr/do/wpgate/gwia/dsnhold*', '')]
            }
        ),
        (
            'random_files', {
                'group_patterns': [('/gw/ro-gr/do/wpgate/gwia/dsnhold*', '')]
            }
        ),
        (
            'random_files', {
                'group_patterns': [('/gw/ro-gr/do/wpgate/gwia/dsnhold*', '')]
            }
        )
    ]
}

checks = {
    'groups': [
        (
            'random_files', {
                'maxsize_largest': (300, 400),
                'group_patterns': [('/gw/ro-gr/do/wpgate/gwia/dsnhold*', '')],
                'additional_rules': [('/gw/ro-gr/do/wpgate/gwia/dsnhold/5753717f.*', {'maxsize_largest': (1, 2)}),],
                'shorten_multiline_output': True,
            }, [
                (0, 'Count: 4', [('count', 4, None, None, None, None)]),
                (0, 'Size: 1536 B', [('size', 1536, None, None, None, None)]),
                (
                    1, 'Largest size: 384 B (warn/crit at 300 B/400 B)', [
                        ('size_largest', 384, 300.0, 400.0, None, None)
                    ]
                ),
                (
                    0, 'Smallest size: 384 B', [
                        ('size_smallest', 384, None, None, None, None)
                    ]
                ),
                (
                    0, 'Oldest age: 3.1 y', [
                        ('age_oldest', 98175428, None, None, None, None)
                    ]
                ),
                (
                    0, 'Newest age: 3.1 y', [
                        ('age_newest', 98160404, None, None, None, None)
                    ]
                ),
                (
                    0, 'Files matching /gw/ro-gr/do/wpgate/gwia/dsnhold/5753717f.*'
                ),
                (0, 'Count: 1', [('count', 1, None, None, None, None)]),
                (0, 'Size: 384 B', [('size', 384, None, None, None, None)]),
                (2, 'Largest size: 384 B (warn/crit at 1 B/2 B)', [('size_largest', 384, 1, 2, None, None)]),
                (
                    0, 'Smallest size: 384 B', [
                        ('size_smallest', 384, None, None, None, None)
                    ]
                ),
                (
                    0, 'Oldest age: 3.1 y', [
                        ('age_oldest', 98209582, None, None, None, None)
                    ]
                ),
                (
                    0, 'Newest age: 3.1 y', [
                        ('age_newest', 98209582, None, None, None, None)
                    ]
                ),
                (   0, '\nInclude patterns: /gw/ro-gr/do/wpgate/gwia/dsnhold*\nFiles matching /gw/ro-gr/do/wpgate/gwia/dsnhold/5753717f.*:\n[/gw/ro-gr/do/wpgate/gwia/dsnhold/5753717f.000] Age: 3.1 y, Size: 384 B(!!)\n(Remaining) files in file group:\n[/gw/ro-gr/do/wpgate/gwia/dsnhold/5753f6e9.000] Age: 3.1 y, Size: 384 B(!)\n[/gw/ro-gr/do/wpgate/gwia/dsnhold/5754104f.000] Age: 3.1 y, Size: 384 B(!)\n[/gw/ro-gr/do/wpgate/gwia/dsnhold/57543199.000] Age: 3.1 y, Size: 384 B(!)'
                )
            ]
        )
    ]
}

mock_host_conf = {
    '': [[('random_files', ('/gw/ro-gr/do/wpgate/gwia/dsnhold*', ''))]],
    'groups': [[('random_files', ('/gw/ro-gr/do/wpgate/gwia/dsnhold*', ''))]]
}
