#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'lparstat_aix'


info = [[u'System',
         u'configuration:',
         u'type=Dedicated',
         u'mode=Capped',
         u'smt=4',
         u'lcpu=4',
         u'mem=16384MB'],
        [u'%user', u'%sys', u'%wait', u'%idle'],
        [u'-----', u'-----', u'------', u'------'],
        [u'0.1', u'58.8', u'0.0', u'41.1']]


discovery = {'': [], 'cpu_util': [(None, {})]}


checks = {'cpu_util': [(None,
                        {},
                        [(0, 'User: 0.1%', [('user', 0.1, None, None, None, None)]),
                         (0,
                          'System: 58.8%',
                          [('system', 58.8, None, None, None, None)]),
                         (0, 'Wait: 0%', [('wait', 0.0, None, None, None, None)]),
                         (0,
                          'Total CPU: 58.9%',
                          [('util', 58.9, None, None, 0, None)])])]}
