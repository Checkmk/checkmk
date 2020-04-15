#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ipmi_sensors'

info = [
    ['162', '01-Inlet Ambient', 'Temperature', '24.00', 'C', 'OK'],
    ['171', 'Intrusion', 'Physical Security', 'N/A', '', 'OK'],
    ['172', 'SysHealth_Stat', 'Chassis', 'N/A', '', 'OK'],
    ['174', 'UID', 'UNKNOWN type 192', 'N/A', '', 'no state reported'],
    ['182', 'Power Meter', 'Other', '260.00', 'W', 'OK'],
    ['72', 'Memory Status', 'Memory', 'N/A', 'error', 'OK'],
    ['187', 'Megacell Status', 'Battery', 'N/A', '', 'OK'],
    ['35', 'CPU Utilization', 'Processor', '68.00', '', 'OK']
]

discovery = {
    '': [
        ('01-Inlet_Ambient', {}), ('CPU_Utilization', {}), ('Intrusion', {}),
        ('Megacell_Status', {}), ('Memory_Status', {}), ('Power_Meter', {}),
        ('SysHealth_Stat', {}), ('UID', {})
    ]
}

checks = {
    '': [
        (
            '01-Inlet_Ambient', {}, [
                (0, 'Status: OK', []),
                (0, '24.00 C', [('value', 24.0, None, None, None, None)])
            ]
        ), ('CPU_Utilization', {}, [(0, 'Status: OK', []), (0, '68.00', [])]),
        ('Intrusion', {}, [(0, 'Status: OK', [])]),
        ('Megacell_Status', {}, [(0, 'Status: OK', [])]),
        ('Memory_Status', {}, [(0, 'Status: OK', [])]),
        ('Power_Meter', {}, [(0, 'Status: OK', []), (0, '260.00 W', [])]),
        ('SysHealth_Stat', {}, [(0, 'Status: OK', [])]),
        ('UID', {}, [(2, 'Status: no state reported', [])])
    ]
}
