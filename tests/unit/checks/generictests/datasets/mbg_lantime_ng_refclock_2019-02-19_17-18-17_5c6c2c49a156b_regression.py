#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'mbg_lantime_ng_refclock'


info = [[u'1',
         u'15',
         u'3',
         u'2',
         u'101',
         u'0',
         u'0',
         u'0',
         u'0',
         u'0',
         u'not announced']]


discovery = {'': [(u'1', None)], 'gps': []}


checks = {'': [(u'1',
                {},
                [(1,
                  'Type: tcr511, Usage: primary, State: not synchronized (TCT sync)',
                  [])])]}
