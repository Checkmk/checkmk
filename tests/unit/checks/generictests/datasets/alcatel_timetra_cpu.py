#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'alcatel_timetra_cpu'

info = [['92']]

discovery = {'': [(None, 'alcatel_timetra_cpu_default_levels')]}

checks = {
    '': [(None, (90.0, 95.0), [(1, 'Total CPU: 92.00% (warn/crit at 90.00%/95.00%)',
                                [('util', 92, 90.0, 95.0, 0, 100)])])]
}
