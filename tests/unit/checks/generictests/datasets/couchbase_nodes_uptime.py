#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'couchbase_nodes_uptime'

freeze_time = '2019-10-23 14:49:25'

info = [
    [u'ignore_this_for_shortess'], [u'invalid number', u'ladida'],
    [u'123', u'Node', u'with', u'weird', u'hostname']
]

discovery = {'': [(u'Node with weird hostname', {})]}

checks = {
    '': [
        (
            u'Node with weird hostname', {}, [
                (
                    0, 'Up since Wed Oct 23 16:47:22 2019, uptime: 0:02:03', [
                        ('uptime', 123.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
