#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.systemtime import parse_systemtime

checkname = 'systemtime'

freeze_time = '2020-10-10 20:38:55'

parsed = parse_systemtime([['1593509210']])

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, (30, 60), [
                (
                    2, 'Offset: -102 days 11 hours (warn/crit below -30 seconds/-1 minute 0 seconds)', [
                        ('offset', -8853125, 30.0, 60.0, None, None)
                    ]
                )
            ]
        )
    ]
}
