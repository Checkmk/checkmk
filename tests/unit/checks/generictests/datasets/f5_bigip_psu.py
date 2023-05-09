#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'f5_bigip_psu'

info = [['1', '1'], ['2', '1']]

discovery = {'': [('1', None), ('2', None)]}

checks = {
    '': [
        ('1', {}, [(0, 'PSU state: good', [])]),
        ('2', {}, [(0, 'PSU state: good', [])])
    ]
}
