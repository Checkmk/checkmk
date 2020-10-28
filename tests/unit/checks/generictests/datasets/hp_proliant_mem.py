#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.hp_proliant_mem import Module

checkname = 'hp_proliant_mem'

parsed = {
    '0': Module(number='0', board='0', cpu_num=1, size=4294967296,
                typ='DIMM DDR3', serial='', status='good', condition='ok'),
    '3': Module(number='3', board='0', cpu_num=1, size=0,
                typ='DIMM DDR3', serial='', status='  notPresent', condition='other'),                 '8': Module(number='8', board='0', cpu_num=2, size=4294967296, typ='DIMM DDR3',
                serial='',   status='good', condition='ok'),
    '9': Module(number='9', board='0', cpu_num=2, size=0, typ='DIMM DDR3', serial='',
                status='  notPresent', condition='other'),
}

discovery = {
    '': [
        ('0', {}),
        ('8', {}),
    ]
}

checks = {
    '': [
        ('0', {}, [
            (0, 'Board: 0', []),
            (0, 'Number: 0', []),
            (0, 'Type: DIMM DDR3', []),
            (0, 'Size: 4.00 GB', []),
            (0, 'Status: good', []),
            (0, 'Condition: ok', []),
        ]),
    ],
}
