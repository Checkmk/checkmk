#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'hp_proliant_cpu'

info = [['0', '0', 'Intel Xeon', '2'], ['1', '0', 'Intel Xeon', '2']]

discovery = {'': [('0', None), ('1', None)]}

checks = {
    '': [
        ('0', {}, [(0, 'CPU0 "Intel Xeon" in slot 0 is in state "ok"', [])]),
        ('1', {}, [(0, 'CPU1 "Intel Xeon" in slot 0 is in state "ok"', [])])
    ]
}
