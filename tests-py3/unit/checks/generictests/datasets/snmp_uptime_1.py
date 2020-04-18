#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'snmp_uptime'

freeze_time = '1970-02-12 22:59:33'

info = [['2297331594', '']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (
                    0,
                    'Up since Fri May 23 02:30:58 1969, uptime: 265 days, 21:28:35',
                    [('uptime', 22973315, None, None, None, None)]
                )
            ]
        )
    ]
}
