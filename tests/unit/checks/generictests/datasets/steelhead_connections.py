#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = "steelhead_connections"

info = [
    [u'1.0', u'1619'],
    [u'2.0', u'1390'],
    [u'3.0', u'0'],
    [u'4.0', u'4'],
    [u'5.0', u'1615'],
    [u'6.0', u'347'],
    [u'7.0', u'3009'],
]


discovery = {
    '': [(None, {})],
}


checks = {
    '': [
        (None, {}, [
            (0, 'Total connections: 3009', []),
            (0, 'Passthrough: 1390', [('passthrough', 1390)]),
            (0, 'Optimized: 1619', []),
            (0, 'Active: 347', [('active', 347)]),
            (0, 'Established: 1615', [('established', 1615)]),
            (0, 'Half opened: 0', [('halfOpened', 0)]),
            (0, 'Half closed: 4', [('halfClosed', 4)]),
        ]),
    ],
}
