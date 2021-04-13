#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ups_cps_inphase'

info = [['32', 'NULL']]

discovery = {'': [('1', {})]}

checks = {
    '': [
        (
            '1', {}, [
                (
                    0, 'Voltage: 3.2 V', [
                        ('voltage', 3.2, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
