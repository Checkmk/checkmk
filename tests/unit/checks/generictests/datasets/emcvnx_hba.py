#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'emcvnx_hba'


parsed = {u'SP A Port 0': {u'Blocks Read': 0, u'Blocks Written': 0},
          u'SP B Port 0': {},
          u'SP B Port 3': {}}


discovery = {'': [(u'SP A Port 0', None)]}


checks = {'': [(u'SP A Port 0',
                {},
                [(0,
                  'Read: 0 Blocks/s, Write: 0 Blocks/s',
                  [('read_blocks', 0, None, None, None, None),
                   ('write_blocks', 0, None, None, None, None)])])]}
