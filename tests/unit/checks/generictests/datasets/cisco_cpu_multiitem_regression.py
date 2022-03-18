#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'cisco_cpu_multiitem'


info = [[[u'1008', u'24'], ['4001', '10']],
        [['1008', 'CPU 7', '12'], ['4001', 'I AM A FAN, please do not discover me as CPU...', '7']]]


discovery = {'': [(u'7', {})]}


checks = {'': [(u'7',
                {'levels': (80.0, 90.0)},
                [(0,
                    'Utilization in the last 5 minutes: 24.0%',
                  [('util', 24.0, 80.0, 90.0, 0, 100)])])]}
