#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.ps_section import parse_ps

# yapf: disable
# type: ignore
checkname = 'ps'

parsed = parse_ps([
    [
        '(\\\\DUBETFUTIL502\\ntpservice,31108,6140,0,300,2,312500,1250000,105,5,16517)',
        'C:\\Program', 'Files', '(x86)\\NTP\\bin\\ntpd.exe', '-U', '3', '-M',
        '-c', 'C:\\Program', 'Files', '(x86)\\NTP\\etc\\ntp.conf'
    ]
])

discovery = {
    '': [
        (
            'NTP', {
                'process':
                '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*',
                'match_groups': (None, 'NTP'),
                'user': None,
                'cgroup': (None, False),
                'cpu_rescale_max': None
            }
        )
    ],
    'perf': []
}

checks = {
    '': [
        (
            'NTP', {
                'process':
                '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*',
                'cpu_rescale_max': None,
                'match_groups': [None, 'NTP'],
                'levels': (1, 1, 1, 1),
                'user': None
            }, [
                (0, 'Processes: 1', [('count', 1, 2.0, 2.0, 0.0, None)]),
                (
                    0, 'virtual: 30.38 MB', [
                        ('vsz', 31108, None, None, None, None)
                    ]
                ),
                (
                    0, 'physical: 6.00 MB', [
                        ('rss', 6140, None, None, None, None)
                    ]
                ), (0, 'CPU: 0%', [('pcpu', 0.0, None, None, None, None)]),
                (
                    0, 'process handles: 105', [
                        ('process_handles', 105, None, None, None, None)
                    ]
                ), (0, 'running for: 275 m', [])
            ]
        ),
        (
            'NTP', {
                'levels': (1, 1, 99999, 99999),
                'process':
                '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*',
                'match_groups': (None, 'NTP'),
                'user': None,
                'cgroup': (None, False),
                'cpu_rescale_max': None
            }, [
                (
                    0, 'Processes: 1', [
                        ('count', 1, 100000.0, 100000.0, 0.0, None)
                    ]
                ),
                (
                    0, 'virtual: 30.38 MB', [
                        ('vsz', 31108, None, None, None, None)
                    ]
                ),
                (
                    0, 'physical: 6.00 MB', [
                        ('rss', 6140, None, None, None, None)
                    ]
                ), (0, 'CPU: 0%', [('pcpu', 0.0, None, None, None, None)]),
                (
                    0, 'process handles: 105', [
                        ('process_handles', 105, None, None, None, None)
                    ]
                ), (0, 'running for: 275 m', [])
            ]
        )
    ]
}

extra_sections = {'': [[], [], [], [], []]}  # type: ignore

mock_host_conf = {
    '': {
        'cpu_rescale_max': None,
        'match':
        '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*',
        'descr': '%1%2'
    }
}
