#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ups_cps_battery'


info = [[u'73', u'41', u'528000']]


discovery = {'': [(None, {})], 'temp': [('Battery', {})]}


checks = {'': [(None,
                {'capacity': (95, 90)},
                [(2, 'Capacity at 73% (warn/crit at 95/90%)', []),
                 (0, '88 minutes remaining on battery', [])])],
          'temp': [('Battery',
                    {},
                    [(0, u'41 \xb0C', [('temp', 41, None, None, None, None)])])]}
