#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'uptime'

freeze_time = '1970-02-12 22:59:33'

info = [['3707973.23', '3707973.23']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (
                    0,
                    'Up since Thu Jan  1 01:59:59 1970, uptime: 42 days, 21:59:33',
                    [('uptime', 3707973.23, None, None, None, None)]
                )
            ]
        )
    ]
}
