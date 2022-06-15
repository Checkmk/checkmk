#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'pulse_secure_cpu_util'

info = [['1']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'util': (80.0, 90.0)
            }, [(0, 'Total CPU: 1.00%', [('util', 1, 80.0, 90.0, 0, 100)])]
        )
    ]
}
