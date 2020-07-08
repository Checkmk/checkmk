#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore

checkname = 'ups_capacity'

info = [['0', '0', '97']]

discovery = {'': [(None, 'ups_capacity_default_levels')]}

checks = {
    '': [(
        None,
        {
            'battime': (0, 0),
            'capacity': (95, 90)
        },
        [
            (0, 'on mains', []),
            (0, 'Percent: 97.0%', [('percent', 97, None, None, None, None)]),
        ],
    ),]
}
