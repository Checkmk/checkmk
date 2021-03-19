#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore

checkname = 'docker_container_cpu'

info = [[
    '@docker_version_info',
    '{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.40"}'
],
        [
            '{"cpu_usage": {"total_usage": 0, "usage_in_kernelmode": 0, "usage_in_usermode": 0}, '
            '"throttling_data": {"throttled_time": 0, "periods": 0, "throttled_periods": 0}}'
        ]]

discovery = {'': []}

checks = {
    '': [],
}

mock_item_state = {'': (0, 0)}
