#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.mem import parse_proc_meminfo_bytes

# yapf: disable
# type: ignore

checkname = 'mem'

parsed = parse_proc_meminfo_bytes([
    ['MemTotal:', '33553908', 'kB'], ['MemFree:', '16791060', 'kB'],
    ['SwapTotal:', '65536000', 'kB'], ['SwapFree:', '62339136', 'kB'],
    ['PageTotal:', '99089908', 'kB'], ['PageFree:', '79130196', 'kB'],
    ['VirtualTotal:', '2097024', 'kB'], ['VirtualFree:', '2055772', 'kB']
])

discovery = {'win': [(None, {})], 'used': [], 'vmalloc': [], 'linux': []}

checks = {
    'win': [
        (
            None, {
                'memory': (80.0, 90.0),
                'pagefile': (80.0, 90.0)
            }, [
                (
                    0, 'RAM: 49.96% - 15.99 GB of 32.00 GB', [
                        ('mem_used', 17165156352, None, None, 0, 34359201792),
                        (
                            'mem_used_percent', 49.95796018752868, None, None,
                            0.0, None
                        ),
                        ('mem_total', 32767.48828125, None, None, None, None)
                    ]
                ),
                (
                    0, 'Commit charge: 20.14% - 19.04 GB of 94.50 GB', [
                        (
                            'pagefile_used', 20438745088, None, None, 0,
                            101468065792
                        ),
                        (
                            'pagefile_total', 96767.48828125, None, None, None,
                            None
                        )
                    ]
                )
            ]
        )
    ]
}
