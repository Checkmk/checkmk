#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'ps'

info = [
    [
        None,
        '(\\\\DUBETFUTIL502\\ntpservice,31108,6140,0,300,2,312500,1250000,105,5,16517)',
        'C:\\Program', 'Files', '(x86)\\NTP\\bin\\ntpd.exe', '-U', '3', '-M',
        '-c', 'C:\\Program', 'Files', '(x86)\\NTP\\etc\\ntp.conf'
    ]
]

discovery = {
    '': [
        (
            'NTP', {
                'process':
                '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*',
                'cpu_rescale_max': None,
                'match_groups': (None, 'NTP'),
                'user': None,
                'cgroup': (None, False)
            }
        )
    ],
    'perf': []
}

checks = {
    '': [
        (
            u'NTP', {
                'process':
                '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*',
                'cpu_rescale_max': None,
                'match_groups': [None, u'NTP'],
                'levels': (1, 1, 1, 1),
                'user': None
            }, [
                (0, '1 process', [('count', 1, 2, 2, 0, None)]),
                (
                    0, '30.38 MB virtual', [
                        ('vsz', 31108, None, None, None, None)
                    ]
                ),
                (
                    0, '6.00 MB physical', [
                        ('rss', 6140, None, None, None, None)
                    ]
                ), (0, '0.0% CPU', [('pcpu', 0.0, None, None, None, None)]),
                (
                    0, '105 process handles', [
                        ('process_handles', 105, None, None, None, None)
                    ]
                ), (0, 'running for 275 m', [])
            ]
        ),
        (
            'NTP', {
                'cpu_rescale_max':
                None,
                'match_groups': (None, 'NTP'),
                'levels': (1, 1, 99999, 99999),
                'user':
                None,
                'cgroup': (None, False),
                'process':
                '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*'
            }, [
                (0, '1 process', [('count', 1, 100000, 100000, 0, None)]),
                (
                    0, '30.38 MB virtual', [
                        ('vsz', 31108, None, None, None, None)
                    ]
                ),
                (
                    0, '6.00 MB physical', [
                        ('rss', 6140, None, None, None, None)
                    ]
                ), (0, '0.0% CPU', [('pcpu', 0.0, None, None, None, None)]),
                (
                    0, '105 process handles', [
                        ('process_handles', 105, None, None, None, None)
                    ]
                ), (0, 'running for 275 m', [])
            ]
        )
    ]
}

extra_sections = {'': [[], [], [], [], [], []]}

mock_host_conf = {
    '': {
        'cpu_rescale_max': None,
        'match':
        '~.*STS\\\\Service.*(SIGTimeService).exe$|C:\\\\Program\\sFiles\\s\\(x86\\)\\\\(NTP)\\\\bin\\\\ntpd\\.exe.*',
        'descr': '%1%2'
    }
}
