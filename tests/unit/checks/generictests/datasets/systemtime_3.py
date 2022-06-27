#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.systemtime import parse_systemtime

checkname = 'systemtime'

parsed = parse_systemtime([['1593509210.123', '1593509209.34534']])

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {'levels': (30, 60)}, [
                (
                    0, 'Offset: 778 milliseconds', [
                        ('offset', 0.7776598930358887, 30.0, 60.0, None, None)
                    ]
                )
            ]
        )
    ]
}
