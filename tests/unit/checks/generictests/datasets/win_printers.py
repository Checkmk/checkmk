#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'win_printers'


info = [
    ['PrinterStockholm', '3', '4', '0'],
    ['Printer', 'Berlin', '3', '4', '0'],
    ['WH1_BC_O3_UPS', '0', '3', '8'],
    ['"printerstatus","detectederrorstate"',
     '-Type',
     'OnlyIfInBoth',
     '|',
     'format-table',
     '-HideTableHeaders']
]


discovery = {'': [('PrinterStockholm', {}), ('Printer Berlin', {}), ('WH1_BC_O3_UPS', {})]}


checks = {'': [('PrinterStockholm',
                {'crit_states': [9, 10], 'warn_states': [8, 11]},
                [(0, '3 jobs current, State: Printing, ', [])]),
               ('Printer Berlin',
                {'crit_states': [9, 10], 'warn_states': [8, 11]},
                [(0, '3 jobs current, State: Printing, ', [])]),
               ('WH1_BC_O3_UPS',
                {'crit_states': [9, 10], 'warn_states': [8, 11]},
                [(1, '0 jobs current, State: Idle, Error State: Jammed(!)', [])])]}
