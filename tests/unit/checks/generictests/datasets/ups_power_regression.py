#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ups_power'

info = [['1', '1', '2'], ['2', '0', '2'], ['3', '1', '0'], ['4', '0', '0']]

discovery = {
    '': [('1', 'ups_power_default_levels'), ('3', 'ups_power_default_levels')]
}

checks = {
    '': [
        (
            '1', (20, 1), [
                (
                    1, 'power: 2W (warn/crit at 20W/1W)', [
                        ('power', 2, 20, 1, 0, None)
                    ]
                )
            ]
        ),
        (
            '3', (20, 1), [
                (
                    2, 'power: 0W (warn/crit at 20W/1W)', [
                        ('power', 0, 20, 1, 0, None)
                    ]
                )
            ]
        )
    ]
}
