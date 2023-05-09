#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'juniper_bgp_state'

info = [
    [
        u'4', u'1',
        [
            u'222', u'173', u'190', u'239', u'0', u'64', u'1', u'17', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'1'
        ]
    ],
    [u'4', u'2', [u'0'] * 16],
]

discovery = {'': [('[dead:beef:40:111::1]', {}), ("[::]", {})]}

checks = {
    '': [
        (
            '[dead:beef:40:111::1]',
            {},
            [
                (0, 'Status with peer [dead:beef:40:111::1] is opensent', []),
                (1, 'operational status: halted', []),
            ],
        ),
        (
            u"[::]",
            {},
            [
                (2, u"Status with peer [::] is opensent", []),
                (0, 'operational status: running', []),
            ],
        ),
    ]
}
