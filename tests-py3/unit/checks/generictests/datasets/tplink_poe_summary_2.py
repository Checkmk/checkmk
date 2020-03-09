#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'tplink_poe_summary'

info = [[u'900']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, (90, 100), [
                (1, '90.00 Watt (warn/crit at 90.00 Watt/100.00 Watt)', [('power', 90.0, 90.0, 100.0)])
            ]
        )
    ]
}
