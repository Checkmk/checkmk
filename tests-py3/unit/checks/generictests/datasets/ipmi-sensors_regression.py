#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'ipmi_sensors'


info = [[u'162', u'01-Inlet Ambient', u'Temperature', u'24.00', u'C', u'OK'],
        [u'171', u'Intrusion', u'Physical Security', u'N/A', u'', u'OK'],
        [u'172', u'SysHealth_Stat', u'Chassis', u'N/A', u'', u'OK'],
        [u'174', u'UID', u'UNKNOWN type 192', u'N/A', u'', u'no state reported'],
        [u'182', u'Power Meter', u'Other', u'260.00', u'W', u'OK'],
        [u'72', u'Memory Status', u'Memory', u'N/A', u'error', u'OK'],
        [u'187', u'Megacell Status', u'Battery', u'N/A', u'', u'OK'],
        [u'35', u'CPU Utilization', u'Processor', u'68.00', u'', u'OK']]


discovery = {'': [(u'01-Inlet_Ambient', {}),
                  (u'CPU_Utilization', {}),
                  (u'Intrusion', {}),
                  (u'Megacell_Status', {}),
                  (u'Memory_Status', {}),
                  (u'Power_Meter', {}),
                  (u'SysHealth_Stat', {}),
                  (u'UID', {})]}


checks = {'': [(u'01-Inlet_Ambient',
                {},
                [(0,
                  u'Status: OK, 24.0 C',
                  [('value', 24.0, None, None, None, None)])]),
               (u'CPU_Utilization', {}, [(0, u'Status: OK, 68.0 ', [])]),
               (u'Intrusion', {}, [(0, u'Status: OK', [])]),
               (u'Megacell_Status', {}, [(0, u'Status: OK', [])]),
               (u'Memory_Status', {}, [(0, u'Status: OK', [])]),
               (u'Power_Meter', {}, [(0, u'Status: OK, 260.0 W', [])]),
               (u'SysHealth_Stat', {}, [(0, u'Status: OK', [])]),
               (u'UID', {}, [(2, u'Status: no state reported', [])])]}
