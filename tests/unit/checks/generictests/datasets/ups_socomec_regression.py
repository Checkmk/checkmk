#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ups_socomec_in_voltage'


info = [[u'1', u'2300']]


discovery = {'': [(u'1', 'ups_in_voltage_default_levels')]}


checks = {'': [(u'1',
                (210, 180),
                [(0,
                  'in voltage: 230V, (warn/crit at 210V/180V)',
                  [('in_voltage', 230, 210, 180, 150, None)])])]}
