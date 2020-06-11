#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'domino_tasks'

info = [
    ['Node', 'Directory Indexer'], ['Node', 'DAOS Manager'],
    ['Node', 'DAOS Manager'], ['Node', 'Event Monitor']
]

discovery = {
    '': [
        (
            'DAOS Manager', {
                'process': 'DAOS Manager',
                'match_groups': (),
                'user': None,
                'cgroup': (None, False),
                'cpu_rescale_max': None,
                'levels': (1, 3, 6, 20)
            }
        )
    ]
}

checks = {
    '': [
        (
            'DAOS Manager', {
                'process': 'DAOS Manager',
                'match_groups': (),
                'user': None,
                'cgroup': (None, False),
                'cpu_rescale_max': None,
                'levels': (1, 3, 6, 20)
            }, [
                (
                    1, 'Tasks: 2 (warn/crit below 3/1) [running on Node]', [
                        ('count', 2, 7.0, 21.0, 0.0, None)
                    ]
                ), (0, 'CPU: 0%', [('pcpu', 0.0, None, None, None, None)])
            ]
        )
    ]
}

mock_host_conf = {
    '': {
        'cpu_rescale_max': None,
        'descr': 'DAOS Manager',
        'levels': (1, 3, 6, 20),
        'match': 'DAOS Manager'
    }
}
