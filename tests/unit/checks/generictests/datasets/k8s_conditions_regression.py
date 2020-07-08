#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'k8s_conditions'

info = [[
    u'{"DiskPressure": "False", "OutOfDisk": "False", "MemoryPressure": "False", "Ready": "False", "NetworkUnavailable": "False", "KernelDeadlock": "True"}'
]]

discovery = {
    '': [(u'DiskPressure', {}), (u'KernelDeadlock', {}), (u'MemoryPressure', {}),
         (u'NetworkUnavailable', {}), (u'OutOfDisk', {}), (u'Ready', {})]
}

checks = {
    '': [(u'DiskPressure', {}, [(0, u'False', [])]), (u'KernelDeadlock', {}, [(2, u'True', [])]),
         (u'MemoryPressure', {}, [(0, u'False', [])]),
         (u'NetworkUnavailable', {}, [(0, u'False', [])]), (u'OutOfDisk', {}, [(0, u'False', [])]),
         (u'Ready', {}, [(2, u'False', [])])]
}
