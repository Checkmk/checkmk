#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import OrderedDict

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.esx_vsphere_hostsystem_cpu_usage import (
    check_esx_vsphere_hostsystem_cpu,
    discover_esx_vsphere_hostsystem_cpu_usage,
)


@pytest.mark.parametrize('section, discovered_service', [
    (
        OrderedDict([
            ('hardware.cpuInfo.hz', ['2199999833']),
            ('hardware.cpuInfo.numCpuCores', ['20']),
            ('hardware.cpuInfo.numCpuPackages', ['2']),
            ('hardware.cpuInfo.numCpuThreads', ['40']),
            ('summary.quickStats.overallCpuUsage', ['3977']),
        ]),
        [Service()],
    ),
    (
        OrderedDict([
            ('hardware.cpuInfo.hz', ['2199999833']),
            ('hardware.cpuInfo.numCpuCores', ['20']),
            ('hardware.cpuInfo.numCpuPackages', ['2']),
            ('hardware.cpuInfo.numCpuThreads', ['40']),
        ]),
        [],
    ),
])
def test_discover_esx_vsphere_hostsystem_cpu_usage(section, discovered_service):
    assert list(discover_esx_vsphere_hostsystem_cpu_usage(section, None)) == discovered_service


@pytest.mark.parametrize('section, check_results', [
    (
        OrderedDict([
            ('hardware.cpuInfo.hz', ['2199999833']),
            ('hardware.cpuInfo.numCpuCores', ['20']),
            ('hardware.cpuInfo.numCpuPackages', ['2']),
            ('hardware.cpuInfo.numCpuThreads', ['40']),
            ('summary.quickStats.overallCpuUsage', ['3977']),
        ]),
        [
            Result(state=State.OK, summary='Total CPU: 9.04%'),
            Metric('util', 9.038637049751086, boundaries=(0.0, None)),
            Result(state=State.OK, notice='3.98 GHz/44.0 GHz'),
            Result(state=State.OK, notice='Sockets: 2'),
            Result(state=State.OK, notice='Cores/socket: 10'),
            Result(state=State.OK, notice='Threads: 40'),
        ],
    ),
])
def test_check_esx_vsphere_hostsystem_cpu(section, check_results):
    assert list(check_esx_vsphere_hostsystem_cpu({}, section, None)) == check_results
