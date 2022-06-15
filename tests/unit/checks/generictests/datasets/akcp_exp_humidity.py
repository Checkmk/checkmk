#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'akcp_exp_humidity'


info = [[u'Dual Humidity Port 1', u'30', u'7', u'1']]


discovery = {'': [(u'Dual Humidity Port 1', 'akcp_humidity_defaultlevels')]}


checks = {'': [(u'Dual Humidity Port 1',
                (30, 35, 60, 65),
                [(2, 'State: sensor error', []),
                 (1,
                  '30.00% (warn/crit below 35.00%/30.00%)',
                  [('humidity', 30, 60, 65, 0, 100)])])]}
