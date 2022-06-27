#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'vutlan_ems_humidity'

info = [[['101001', 'Dry-1', '0'], ['101002', 'Dry-2', '0'], ['101003', 'Dry-3', '0'], ['101004', 'Dry-4', '0'], ['106001', 'Analog-5', '0'], ['107001', 'Analog-6', '0'], ['201001', 'Onboard Temperature', '32.80'], ['201002', 'Analog-1', '22.00'], ['201003', 'Analog-2', '22.10'], ['202001', 'Analog-3', '46.20'], ['202002', 'Analog-4', '42.10'], ['203001', 'Onboard Voltage DC', '12.06'], ['301001', 'Analog Power', 'on'], ['304001', 'Power-1', 'off'], ['304002', 'Power-2', 'off'], ['403001', 'USB Web camera', '0']]]

discovery = {'': [('Analog-3', {}), ('Analog-4', {})]}

checks = {
    '': [
        (
            'Analog-3', {
                'levels': (15.0, 16.0)
            }, [
                (
                    2, '46.20% (warn/crit at 15.00%/16.00%)', [
                        ('humidity', 46.2, 15.0, 16.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            'Analog-4', {
                'levels': (50.0, 60.0)
            }, [
                (
                    0, '42.10%', [
                        ('humidity', 42.1, 50.0, 60.0, 0.0, 100.0)
                    ]
                )
            ]
        )
    ]
}
