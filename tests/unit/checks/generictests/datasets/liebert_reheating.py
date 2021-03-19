#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_reheating'


info = [[u'Reheating is awesome!', u'81.3', u'%'],
        [u'This value ignored', u'21.1', u'def C']]


discovery = {'': [(None, {})]}


checks = {
    '': [
        (None, {'levels': (80, 90)}, [
            (1, u'81.30 % (warn/crit at 80.00 %/90.00 %)', [
                ('filehandler_perc', 81.3, 80, 90, None, None),
            ]),
        ]),
    ],
}
