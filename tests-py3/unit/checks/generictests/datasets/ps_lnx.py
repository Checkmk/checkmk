#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
                'cpu_rescale_max': None,
                'match_groups': (),
                'user': None,
                'cgroup': ('~.*systemd', False)
            }
        )
    ],
    'perf': []
}

checks = {
    '': [
        (
            'moooo', {
                'cpu_rescale_max': None,
                'match_groups': (),
                'levels': (1, 1, 99999, 99999),
                'user': None,
                'cgroup': ('~.*systemd', False),
                'process': None
            }, [
                (
                    0, '1 process [running on NODE]', [
                        ('count', 1, 100000, 100000, 0, None)
                    ]
                ),
                (
                    0, '220.74 MB virtual', [
                        ('vsz', 226036, None, None, None, None)
                    ]
                ),
                (
                    0, '9.51 MB physical', [
                        ('rss', 9736, None, None, None, None)
                    ]
                ), (0, '0.0% CPU', [('pcpu', 0.0, None, None, None, None)]),
                (0, 'running for 314 m', [])
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
