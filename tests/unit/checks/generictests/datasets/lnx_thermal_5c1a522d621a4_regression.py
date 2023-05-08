#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'lnx_thermal'


info = [[u'thermal_zone0',
         u'enabled',
         u'acpitz',
         u'8300',
         u'31300',
         u'critical',
         u'9800',
         u'passive'],
        [u'thermal_zone1',
         u'-',
         u'pkg-temp-0',
         u'',
         u'35000',
         u'0',
         u'passive',
         u'0',
         u'passive'],
        [u'thermal_zone2',
         u'-',
         u'pkg-temp-1',
         u'',
         u'40000',
         u'0',
         u'passive',
         u'0',
         u'passive']]


discovery = {'': [(u'Zone 0', {})]}


checks = {'': [(u'Zone 0',
                {'device_levels_handling': 'devdefault', 'levels': (70.0, 80.0)},
                [(0, u'8.3 \xb0C', [('temp', 8.3, 9.8, 31.3, None, None)])])]}
