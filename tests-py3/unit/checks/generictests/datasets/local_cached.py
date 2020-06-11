#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'local'

freeze_time = "2019-04-23 07:45:00"

info = [
    ['node_1', 'cached(1556005301,300)', '0', 'Service_FOO', 'V=1', 'This', 'Check', 'is', 'OK'],
]


discovery = {
    '': [
        ('Service_FOO', {}),
    ],
}
