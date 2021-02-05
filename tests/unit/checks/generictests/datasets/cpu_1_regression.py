#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.cpu import parse_cpu


checkname = 'cpu'

parsed = parse_cpu([[u'0.88', u'0.83', u'0.87', u'2/2148', u'21050', u'8']])

discovery = {
    'loads': [(None, 'cpuload_default_levels')],
    'threads': [(None, {})],
}

checks = {
    'loads': [(
        None,
        (5.0, 10.0),
        [(
            0,
            '15 min load: 0.87 at 8 cores (0.11 per core)',
            [
                ('load1', 0.88, 40.0, 80.0, 0, 8),
                ('load5', 0.83, 40.0, 80.0, 0, 8),
                ('load15', 0.87, 40.0, 80.0, 0, 8),
            ],
        )],
    )],
    'threads': [(
        None,
        {
            'levels': (2000, 4000)
        },
        [(
            1,
            'Count: 2148 threads (warn/crit at 2000 threads/4000 threads)',
            [('threads', 2148, 2000.0, 4000.0, None, None)],
        )],
    )]
}
