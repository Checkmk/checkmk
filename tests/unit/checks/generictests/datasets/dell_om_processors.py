#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'dell_om_processors'


info = [['1', '1', 'Some manufacturer', '1', '0'],
        ['2', '2', 'Some manufacturer', '2', '1'],
        ['3', '3', 'Some manufacturer', '3', '2'],
        ['4', '4', 'Some manufacturer', '4', '32'],
        ['5', '4', 'Some manufacturer', '5', '128'],
        ['6', '5', 'Some manufacturer', '6', '256'],
        ['7', '6', 'Some manufacturer', '7', '512'],
        ['8', '6', 'Some manufacturer', '8', '1024']]


discovery = {'': [('1', None),
                  ('2', None),
                  ('3', None),
                  ('6', None),
                  ('7', None),
                  ('8', None)]}


checks = {'': [('1',
                {},
                [(2,
                  '[Some manufacturer] CPU status: Other, CPU reading: Unknown',
                  [])]),
               ('2',
                {},
                [(2,
                  '[Some manufacturer] CPU status: Unknown, CPU reading: Internal Error',
                  [])]),
               ('3',
                {},
                [(0,
                  '[Some manufacturer] CPU status: Enabled, CPU reading: Thermal Trip',
                  [])]),
               ('6',
                {},
                [(2,
                  '[Some manufacturer] CPU status: BIOS Disabled, CPU reading: Disabled',
                  [])]),
               ('7',
                {},
                [(2,
                  '[Some manufacturer] CPU status: Idle, CPU reading: Terminator Present',
                  [])]),
               ('8',
                {},
                [(2,
                  '[Some manufacturer] CPU status: Idle, CPU reading: Throttled',
                  [])])]}
