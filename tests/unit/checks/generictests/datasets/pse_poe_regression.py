#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'pse_poe'


info = [[u'1', u'420', u'1', u'83'],
        [u'2', u'420', u'1', u'380'],
        [u'3', u'420', u'1', u'419'],
        [u'4', u'0', u'2', u'0'],
        [u'5', u'0', u'3', u'0'],
        [u'6', u'-1', u'1', u'-1']]


discovery = {'': [('1', {}), ('2', {}), ('3', {}), ('4', {}), ('5', {}), ('6', {})]}


checks = {'': [('1',
                {'levels': (90.0, 95.0)},
                [(0,
                  'POE usage (83W/420W): : 19.76%',
                  [('power_usage_percentage',
                    19.761904761904763,
                    90.0,
                    95.0,
                    None,
                    None)])]),
               ('2',
                {'levels': (90.0, 95.0)},
                [(1,
                  'POE usage (380W/420W): : 90.48% (warn/crit at 90.00%/95.00%)',
                  [('power_usage_percentage',
                    90.47619047619048,
                    90.0,
                    95.0,
                    None,
                    None)])]),
               ('3',
                {'levels': (90.0, 95.0)},
                [(2,
                  'POE usage (419W/420W): : 99.76% (warn/crit at 90.00%/95.00%)',
                  [('power_usage_percentage',
                    99.76190476190476,
                    90.0,
                    95.0,
                    None,
                    None)])]),
               ('4',
                {'levels': (90.0, 95.0)},
                [(0, 'Operational status of the PSE is OFF', [])]),
               ('5',
                {'levels': (90.0, 95.0)},
                [(2, 'Operational status of the PSE is FAULTY', [])]),
               ('6',
                {'levels': (90.0, 95.0)},
                [(3,
                  'Device returned faulty data: nominal power: -1, power consumption: -1, operational status: 1',
                  [])])]}
