#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'arista_temp'

info = [
    ['Cpu temp sensor', '1', '568'], ['Cpu board temp sensor', '1', '470'],
    ['Back-panel temp sensor', '1', '450'],
    ['Front-panel temp sensor', '1', '304']
]

discovery = {
    '': [
        ('Back-panel temp sensor', {}), ('Cpu board temp sensor', {}),
        ('Cpu temp sensor', {}), ('Front-panel temp sensor', {})
    ]
}

checks = {
    '': [
        (
            'Back-panel temp sensor', {}, [
                (0, '45.0 °C', [('temp', 45.0, None, None, None, None)])
            ]
        ),
        (
            'Cpu board temp sensor', {}, [
                (0, '47.0 °C', [('temp', 47.0, None, None, None, None)])
            ]
        ),
        (
            'Cpu temp sensor', {}, [
                (
                    0, '56.8 °C', [
                        ('temp', 56.800000000000004, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'Front-panel temp sensor', {}, [
                (
                    0, '30.4 °C', [
                        ('temp', 30.400000000000002, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
