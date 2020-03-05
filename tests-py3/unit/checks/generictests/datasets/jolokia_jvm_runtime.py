#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'jolokia_jvm_runtime'

freeze_time = '2019-10-11 08:32:51'

info = [
    [
        u'MyJIRA', u'java.lang:type=Runtime/Uptime,Name',
        u'{"Uptime": 34502762, "Name": "1020@jira"}'
    ]
]

discovery = {'': [(u'MyJIRA', {})]}

checks = {
    '': [
        (
            u'MyJIRA', {}, [
                (
                    0,
                    'Up since Fri Sep  7 02:26:49 2018, uptime: 399 days, 8:06:02',
                    [('uptime', 34502762, None, None, None, None)]
                )
            ]
        )
    ]
}
