#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'stulz_humidity'


info = [[u'MICOS11Q', u'12', u'229376', u'15221', u'15221', u'NO'],
        [u'MICOS11Q', u'12', u'229376', u'15221', u'15221']]


discovery = {'': [(u'MICOS11Q', 'stulz_humidity_default_levels'),
                  (u'MICOS11Q', 'stulz_humidity_default_levels')]}


checks = {'': [(u'MICOS11Q',
                (35, 40, 60, 65),
                [(2,
                  '1.20% (warn/crit below 40.00%/35.00%)',
                  [('humidity', 1.2, 60, 65, 0, 100)])]),
               (u'MICOS11Q',
                (35, 40, 60, 65),
                [(2,
                  '1.20% (warn/crit below 40.00%/35.00%)',
                  [('humidity', 1.2, 60, 65, 0, 100)])])]}
