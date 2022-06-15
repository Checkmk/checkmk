#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'emc_isilon_cpu'

info = [['123', '234', '231', '567']]

discovery = {'': [(None, {})]}

checks = {
    '': [(None, {}, [
        (0, 'User: 35.70%', [('user', 35.7, None, None, None, None)]),
        (0, 'System: 23.10%', [('system', 23.1, None, None, None, None)]),
        (0, 'Interrupt: 56.70%', [('interrupt', 56.7, None, None, None, None)]),
        (0, 'Total: 115.50%', [])
    ]),
       (None, None, [
        (0, 'User: 35.70%', [('user', 35.7, None, None, None, None)]),
        (0, 'System: 23.10%', [('system', 23.1, None, None, None, None)]),
        (0, 'Interrupt: 56.70%', [('interrupt', 56.7, None, None, None, None)]),
        (0, 'Total: 115.50%', [])
    ])]
}
