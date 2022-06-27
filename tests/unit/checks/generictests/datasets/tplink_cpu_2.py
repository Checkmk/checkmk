#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'tplink_cpu'

info = [[u'100']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {'util': (90.0, 100.0)}, [
                (2, 'Total CPU: 100.00% (warn/crit at 90.00%/100.00%)', [('util', 100.0, 90.0, 100.0, 0, 100)])
            ]
        )
    ]
}
