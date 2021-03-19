#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'oracle_logswitches'


info = [['eln',
         'ORACLE_BASE',
         'environment',
         'variable',
         'is',
         'not',
         'being',
         'set',
         'since',
         'this'],
        ['eln',
         'information',
         'is',
         'not',
         'available',
         'for',
         'the',
         'current',
         'user',
         'ID',
         'nagios.'],
        ['eln',
         'You',
         'can',
         'set',
         'ORACLE_BASE',
         'manually',
         'if',
         'it',
         'is',
         'required.'],
        ['eln', '15'],
        ['hirni', '22']]


discovery = {'': [('eln', {}), ('hirni', {})]}


checks = {'': [('eln',
                {'levels': (50, 100), 'levels_lower': (-1, -1)},
                [(0,
                  '15 log switches in the last 60 minutes (warn/crit below -1/-1) (warn/crit at 50/100)',
                  [('logswitches', 15, 50, 100, 0, None)])]),
               ('hirni',
                {'levels': (50, 100), 'levels_lower': (-1, -1)},
                [(0,
                  '22 log switches in the last 60 minutes (warn/crit below -1/-1) (warn/crit at 50/100)',
                  [('logswitches', 22, 50, 100, 0, None)])])]}
