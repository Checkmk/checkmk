#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'hp_proliant_psu'

info = [['0', '1', '3', '2', '80', '460'], ['0', '2', '3', '2', '105', '460']]

discovery = {'': [('0/1', None), ('0/2', None), ('Total', None)]}

checks = {
    '': [
        (
            '0/1', {
                'levels': (80, 90)
            }, [
                (0, 'Chassis 0/Bay 1', []), (0, 'State: "ok"', []),
                (
                    0, 'Usage: 80 Watts', [
                        (
                            'power_usage_percentage', 17.391304347826086, None,
                            None, None, None
                        ), ('power_usage', 80, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            '0/2', {
                'levels': (80, 90)
            }, [
                (0, 'Chassis 0/Bay 2', []), (0, 'State: "ok"', []),
                (
                    0, 'Usage: 105 Watts', [
                        (
                            'power_usage_percentage', 22.82608695652174, None,
                            None, None, None
                        ), ('power_usage', 105, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'Total', {
                'levels': (80, 90)
            }, [
                (
                    0, 'Usage: 185 Watts', [
                        (
                            'power_usage_percentage', 20.108695652173914, None,
                            None, None, None
                        ), ('power_usage', 185, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
