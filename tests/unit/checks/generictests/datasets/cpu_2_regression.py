#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.cpu import parse_cpu


checkname = 'cpu'

parsed = parse_cpu([[u'0.88', u'0.83', u'0.87', u'2/1748', u'21050', u'8'], [u'124069']])

discovery = {
    'threads': [(None, {})],
}

checks = {
    'threads': [(
        None,
        {
            'levels': (2000, 4000)
        },
        [
            (0, 'Count: 1748 threads', [('threads', 1748, 2000.0, 4000.0, None, None)]),
            (0, 'Usage: 1.41%', [('thread_usage', 1.408893438328672, None, None, None, None)]),
        ],
    )],
}
