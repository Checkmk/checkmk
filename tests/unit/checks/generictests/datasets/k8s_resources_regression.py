#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'k8s_resources'

info = [[
    u'{"allocatable": {"pods": 110, "cpu": 0.9400000000000001, "memory": 609845248.0}, "capacity": {"pods": 110, "cpu": 1.0, "memory": 609845248.0}, "requests": {"pods": 0, "cpu": 0.2, "memory": 0.0}, "limits": {"cpu": 0.5, "memory": Infinity}, "allocations": {}}'
]]

discovery = {
    'cpu': [(None, {})],
    'memory': [(None, {})],
    'pods': [(None, {})],
}

checks = {
    'cpu': [(None, {}, [
        (0, 'Request: 0.200', [('k8s_cpu_request', 0.2)]),
        (0, 'Limit: 0.500', [('k8s_cpu_limit', 0.5)]),
        (0, 'Allocatable: 0.940', [('k8s_cpu_allocatable', 0.9400000000000001)]),
        (0, 'Capacity: 1.000', [('k8s_cpu_capacity', 1.0)]),
        (0, 'Usage: 21.28%', [('k8s_cpu_usage', 100.0 * 0.200 / 0.940, None, None, 0.0, None)]),
    ])],
    'memory': [(None, {}, [
        (0, 'Request: 0 B', [('k8s_memory_request', 0.0)]),
        (0, 'Limit: n.a.', []),
        (0, 'Allocatable: 582 MiB', [('k8s_memory_allocatable', 609845248.0)]),
        (0, 'Capacity: 582 MiB', [('k8s_memory_capacity', 609845248.0)]),
        (0, 'Usage: 0%', [('k8s_memory_usage', 0.0, None, None, 0.0, None)]),
    ])],
    'pods': [(None, {}, [
        (0, 'Request: 0', [('k8s_pods_request', 0)]),
        (0, 'Allocatable: 110', [('k8s_pods_allocatable', 110)]),
        (0, 'Capacity: 110', [('k8s_pods_capacity', 110)]),
        (0, 'Usage: 0%', [('k8s_pods_usage', 0.0, None, None, 0.0, None)]),
    ])],
}
