#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ups_out_load'

info = [['1', '1', '2'], ['2', '0', '2'], ['3', '1', '0'], ['4', '0', '0']]

discovery = {
    '': [
        ('1', 'ups_out_load_default_levels'),
        ('3', 'ups_out_load_default_levels')
    ]
}

checks = {
    '': [
        (
            '1', (85, 90), [
                (
                    0, 'load: 2 (warn/crit at 85/90) ', [
                        ('out_load', 2, 85, 90, 100, None)
                    ]
                )
            ]
        ),
        (
            '3', (85, 90), [
                (
                    0, 'load: 0 (warn/crit at 85/90) ', [
                        ('out_load', 0, 85, 90, 100, None)
                    ]
                )
            ]
        )
    ]
}
