#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'juniper_screenos_mem'


info = [[u'157756272', u'541531248']]


discovery = {'': [(None, 'juniper_mem_default_levels')]}


checks = {'': [(None,
                (80.0, 90.0),
                [(0,
                  'Used: 150 MiB/667 MiB (23%)',
                  [('mem_used', 157755392, 559429222.4, 629357875.2, 0, 699286528)])])]}
