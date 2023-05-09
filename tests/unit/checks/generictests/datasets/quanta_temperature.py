#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'quanta_temperature'


info = [[[u'1', u'3', u'Temp_PCI1_Outlet\x01', u'41', u'85', u'80', u'-99', u'-99'],
         [u'2', u'3', u'Temp_CPU0_Inlet', u'37', u'75', u'70', u'-99', u'-99'],
         [u'2', u'3', u'Temp_CPU1_Inlet', u'37', u'75', u'-99', u'-99', u'-99'],
         [u'7', u'1', u'Temp_DIMM_AB', u'-99', u'85', u'84', u'-99', u'-99'],
         [u'7', u'2', u'Temp_DIMM_CD', u'-99', u'85', u'84', u'95', u'100']]]


discovery = {'': [(u'Temp_CPU0_Inlet', {}),
                  (u'Temp_CPU1_Inlet', {}),
                  (u'Temp_DIMM_AB', {}),
                  (u'Temp_DIMM_CD', {}),
                  (u'Temp_PCI1_Outlet', {})]}


checks = {'': [(u'Temp_CPU0_Inlet',
                {},
                [(0, u'37.0 \xb0C', [('temp', 37.0, 70.0, 75.0, None, None)])]),
               (u'Temp_CPU1_Inlet',
                {},
                [(0, u'37.0 \xb0C', [('temp', 37.0, 75.0, 75.0, None, None)])]),
               (u'Temp_DIMM_AB', {}, [(1, 'Status: other', [])]),
               (u'Temp_DIMM_CD', {}, [(3, 'Status: unknown', [])]),
               (u'Temp_PCI1_Outlet',
                {},
                [(0, u'41.0 \xb0C', [('temp', 41.0, 80.0, 85.0, None, None)])])]}
