#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'docker_container_cpu'

info = [
    [
        '@docker_version_info',
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}'
    ],
    [
        '{"cpu_usage": {"total_usage": 422857000, "usage_in_kernelmode": 67657000, "usage_in_usermode": 35520'
        '0000}, "system_cpu_usage": 7609030000000, "online_cpus": 8, "throttling_data": {"periods": 0, "throt'
        'tled_periods": 0, "throttled_time": 0}}'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [(None, {}, [
        (0, 'Total CPU: 0.04%', [
            ('util', 0.044458439512000875, None, None, 0, 800),
        ]),
    ]),],
}

mock_item_state = {'': (0, 0)}
