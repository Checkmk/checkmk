#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'proxmox_mem_usage'

info = [['{"max_mem": 16607309824, "mem": 13449027584}']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {'levels': (80, 90)}, [
                (
                    1,
                    'Usage: 80.98% - 12.53 GB of 15.47 GB (warn/crit at 80.00%/90.00% used)',
                    [
                        ('mem_used', 13449027584.0, 13285847859.2, 14946578841.6, 0, 16607309824.0),
                        ('mem_used_percent', 80.98257771143753, 80.0, 90.0, 0.0, None),
                    ]
                )
            ]
        ),
    ]
}
