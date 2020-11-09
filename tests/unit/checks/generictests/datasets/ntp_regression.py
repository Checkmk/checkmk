#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based import ntp


checkname = 'ntp'


parsed = ntp.parse_ntp([
    ['-', '42.202.61.100', '.INIT.', '16', 'u', '-', '1024', '0', '0.000', '0.000', '0.000'],
])


discovery = {
    '': [],
    'time': [(None, {})],
}


checks = {
    'time': [
        (None, {'alert_delay': (300, 3600), 'ntp_levels': (10, 200.0, 500.0)}, [
            (0, 'Found 1 peers, but none is suitable', []),
            (0, 'Time since last sync: N/A (started monitoring)', []),
        ]),
    ],
}
