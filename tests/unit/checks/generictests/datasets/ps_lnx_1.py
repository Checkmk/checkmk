#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ps'

info = []

discovery = {
    '': [
        (
            'moooo', {
                'process': None,
                'match_groups': (),
                'user': None,
                'cgroup': ('~.*systemd', False),
                'cpu_rescale_max': None
            }
        )
    ],
    'perf': []
}

checks = {
    '': [
        (
            'moooo', {
                'levels': (1, 1, 99999, 99999),
                'process': None,
                'match_groups': (),
                'user': None,
                'cgroup': ('~.*systemd', False),
                'cpu_rescale_max': None
            }, [
                (
                    0, 'Processes: 1 [running on NODE]', [
                        ('count', 1, 100000.0, 100000.0, 0.0, None)
                    ]
                ),
                (
                    0, 'virtual: 220.74 MB', [
                        ('vsz', 226036, None, None, None, None)
                    ]
                ),
                (
                    0, 'physical: 9.51 MB', [
                        ('rss', 9736, None, None, None, None)
                    ]
                ), (0, 'CPU: 0%', [('pcpu', 0.0, None, None, None, None)]),
                (0, 'running for: 314 m', [])
            ]
        ),
        ('moooo', {
            'cgroup': ('~.*systemd', False),
            'cpu_rescale_max': None,
            'levels': (1, 1, 99999, 99999),
            'match_groups': (),
            'process': None,
            'user': None,
            'max_age': (10, 20),
        }, [
                (
                    0, 'Processes: 1 [running on NODE]', [
                        ('count', 1, 100000.0, 100000.0, 0.0, None)
                    ]
                ),
                (
                    0, 'virtual: 220.74 MB', [
                        ('vsz', 226036, None, None, None, None)
                    ]
                ),
                (
                    0, 'physical: 9.51 MB', [
                        ('rss', 9736, None, None, None, None)
                    ]
                ), (0, 'CPU: 0%', [('pcpu', 0.0, None, None, None, None)]),
                (2, 'running for: 314 m (warn/crit at 10.0 s/20.0 s)', [])
            ]
        ),
        ('moooo', {
            'cgroup': ('~.*systemd', False),
            'cpu_rescale_max': None,
            'levels': (1, 1, 99999, 99999),
            'match_groups': (),
            'process': None,
            'user': None,
            'max_age': (10, 20),
            'min_age': (86400, 43200),
        }, [
             (
                 0, 'Processes: 1 [running on NODE]', [
                     ('count', 1, 100000.0, 100000.0, 0.0, None)
                 ]
             ),
             (
                 0, 'virtual: 220.74 MB', [
                     ('vsz', 226036, None, None, None, None)
                 ]
             ),
             (
                 0, 'physical: 9.51 MB', [
                     ('rss', 9736, None, None, None, None)
                 ]
             ), (0, 'CPU: 0%', [('pcpu', 0.0, None, None, None, None)]),
             (2, 'running for: 314 m (warn/crit at 10.0 s/20.0 s)', [])
         ]
         ),
        ('moooo', {
            'cgroup': ('~.*systemd', False),
            'cpu_rescale_max': None,
            'levels': (1, 1, 99999, 99999),
            'match_groups': (),
            'process': None,
            'user': None,
            'min_age': (86400, 43200),
        }, [
             (
                 0, 'Processes: 1 [running on NODE]', [
                     ('count', 1, 100000.0, 100000.0, 0.0, None)
                 ]
             ),
             (
                 0, 'virtual: 220.74 MB', [
                     ('vsz', 226036, None, None, None, None)
                 ]
             ),
             (
                 0, 'physical: 9.51 MB', [
                     ('rss', 9736, None, None, None, None)
                 ]
             ), (0, 'CPU: 0%', [('pcpu', 0.0, None, None, None, None)]),
             (2, 'running for: 314 m (warn/crit below 24 h/12 h)', [])
         ]
         )
    ]
}

extra_sections = {
    '': [
        [
            [
                'NODE', '[header]', 'CGROUP', 'USER', 'VSZ', 'RSS', 'TIME',
                'ELAPSED', 'PID', 'COMMAND'
            ],
            [
                'NODE', '1:name=systemd:/init.scope,', 'root', '226036',
                '9736', '00:00:09', '05:14:30', '1', '/sbin/init', '--ladida'
            ]
        ], [], [], [], [], []
    ]
}

mock_host_conf = {
    '': {
        'cpu_rescale_max': None,
        'descr': 'moooo',
        'cgroup': ('~.*systemd', False)
    }
}
