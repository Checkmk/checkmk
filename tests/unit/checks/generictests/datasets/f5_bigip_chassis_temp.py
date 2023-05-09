#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'f5_bigip_chassis_temp'

info = [['1', '30'], ['2', '32'], ['3', '36'], ['4', '41'], ['5', '41']]

discovery = {
    '': [
        ('1', 'f5_bigip_chassis_temp_default_params'),
        ('2', 'f5_bigip_chassis_temp_default_params'),
        ('3', 'f5_bigip_chassis_temp_default_params'),
        ('4', 'f5_bigip_chassis_temp_default_params'),
        ('5', 'f5_bigip_chassis_temp_default_params')
    ]
}

checks = {
    '': [
        (
            '1', (35, 40), [
                (0, '30 °C', [('temp', 30, 35.0, 40.0, None, None)])
            ]
        ),
        (
            '2', (35, 40), [
                (0, '32 °C', [('temp', 32, 35.0, 40.0, None, None)])
            ]
        ),
        (
            '3', (35, 40), [
                (
                    1, '36 °C (warn/crit at 35/40 °C)', [
                        ('temp', 36, 35.0, 40.0, None, None)
                    ]
                )
            ]
        ),
        (
            '4', (35, 40), [
                (
                    2, '41 °C (warn/crit at 35/40 °C)', [
                        ('temp', 41, 35.0, 40.0, None, None)
                    ]
                )
            ]
        ),
        (
            '5', (35, 40), [
                (
                    2, '41 °C (warn/crit at 35/40 °C)', [
                        ('temp', 41, 35.0, 40.0, None, None)
                    ]
                )
            ]
        )
    ]
}
