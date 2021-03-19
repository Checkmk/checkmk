#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'raritan_pdu_plugs'

info = [[u'1', u'', u'7'], [u'36', u'FooName', u'7']]

discovery = {
    '': [
        (u'1', {'discovered_state': 'on'}),
        (u'36', {'discovered_state': 'on'}),
    ]
}

checks = {
    '': [
        (u'1', 'on', [
            (0, u'Status: on', []),
        ]),
        (u'36', 'on', [
            (0, u'FooName', []),
            (0, u'Status: on', []),
        ]),
        (u'1', 'on', [
            (0, u'Status: on', []),
            ]),
        (u'36', 5, [
            (0, u'FooName', []),
            (0, u'Status: on', []),
            (2, u'Expected: above upper warning', []),
        ]),
    ]
}
