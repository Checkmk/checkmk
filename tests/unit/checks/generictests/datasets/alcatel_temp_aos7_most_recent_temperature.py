#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'alcatel_temp_aos7'

info = [['1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
        ['2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0']]

discovery = {'': [('CPMA', {})]}

checks = {
    '': [('CPMA', {
        'levels': (45, 50)
    }, [(0, u'2 \xb0C', [('temp', 2, 45, 50, None, None)])])]
}
