#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'oracle_rman'


info = [[None,
         u'AFIS2',
         u'COMPLETED',
         u'2016-07-12_02:05:39',
         u'2016-07-12_02:05:39',
         u'DB_INCR',
         u'1',
         u'460',
         u'545791334'],
        [None,
         u'AFIS11',
         u'COMPLETED',
         u'2016-07-12_09:50:46',
         u'2016-07-12_08:08:05',
         u'ARCHIVELOG',
         u'',
         u'103',
         u'']]


discovery = {'': [(u'AFIS11.ARCHIVELOG', {}),
                  (u'AFIS2.DB_INCR_1', {})]}


checks = {'': [(u'AFIS11.ARCHIVELOG',
                {},
                [(0,
                  'Last backup 103 m ago',
                  [('age', 6180, None, None, None, None)])]),
               (u'AFIS2.DB_INCR_1',
                {},
                [(0,
                  'Last backup 7 h ago, incremental SCN 545791334',
                  [('age', 27600, None, None, None, None)])]),
]}
