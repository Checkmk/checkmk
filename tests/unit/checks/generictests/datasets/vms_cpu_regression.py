#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'vms_cpu'

info = [['1', '99.17', '0.54', '0.18', '0.00']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (None, None, [
            (0, 'User: 0.54%', [('user', 0.54)]),
            (0, 'System: 0.11%', [('system', 0.10999999999999827)]),
            (0, 'Wait: 0.18%', [('wait', 0.18)]),
            (0, 'Total CPU: 0.83%', [('util', 0.8299999999999983, None, None, 0, 100)]),
            (0, "100% corresponding to: 1.00 CPU", [('cpu_entitlement', 1)]),
        ]),
        (None, (0.1, 0.5), [
            (0, 'User: 0.54%', [('user', 0.54)]),
            (0, 'System: 0.11%', [('system', 0.10999999999999827)]),
            (1, 'Wait: 0.18% (warn/crit at 0.10%/0.50%)', [('wait', 0.18, 0.1, 0.5)]),
            (0, 'Total CPU: 0.83%', [('util', 0.8299999999999983, None, None, 0, 100)]),
            (0, "100% corresponding to: 1.00 CPU", [('cpu_entitlement', 1)]),
        ]),
    ],
}
