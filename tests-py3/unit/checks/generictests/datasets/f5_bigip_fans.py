#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'f5_bigip_fans'

info = [[['1', '15574'], ['2', '16266'], ['3', '15913'], ['4', '16266']], []]

discovery = {
    '': [
        ('Processor 1', 'f5_bigip_fans_default_levels'),
        ('Processor 2', 'f5_bigip_fans_default_levels'),
        ('Processor 3', 'f5_bigip_fans_default_levels'),
        ('Processor 4', 'f5_bigip_fans_default_levels')
    ]
}

checks = {
    '': [
        ('Processor 1', (2000, 500), [(0, 'speed is 15574 rpm', [])]),
        ('Processor 2', (2000, 500), [(0, 'speed is 16266 rpm', [])]),
        ('Processor 3', (2000, 500), [(0, 'speed is 15913 rpm', [])]),
        ('Processor 4', (2000, 500), [(0, 'speed is 16266 rpm', [])])
    ]
}
