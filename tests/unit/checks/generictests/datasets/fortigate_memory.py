#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'fortigate_memory'

info = [['42']]

discovery = {'': [(None, 'fortigate_memory_default_levels')]}

checks = {
    '': [
        (None, (70, 80), [
            (0, 'Usage: 42.00%', [('mem_usage', 42, 70.0, 80.0, None, None)]),
        ]),
        (None, (30, 80), [
            (1, 'Usage: 42.00% (warn/crit at 30.00%/80.00%)', [('mem_usage', 42, 30.0, 80.0, None, None)]),
        ]),
        (None, (-80, -30), [
            (1, 'Usage: 42.00% (warn/crit at 20.00%/70.00%)', [('mem_usage', 42, 20.0, 70.0, None, None)]),
        ]),
        (None, {"levels": (-80, -30)}, [
            (3, "Absolute levels are not supported", []),
            (0, 'Usage: 42.00%', [('mem_usage', 42, None, None, None, None)]),
        ]),
    ],
}
