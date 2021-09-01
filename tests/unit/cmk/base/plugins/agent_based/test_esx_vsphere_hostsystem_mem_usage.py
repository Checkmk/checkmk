#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import OrderedDict

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.esx_vsphere_hostsystem_mem_usage import (
    check_esx_vsphere_hostsystem_mem_usage,
    discover_esx_vsphere_hostsystem_mem_usage,
)


@pytest.mark.parametrize('section, discovered_service', [
    (
        OrderedDict([
            ('summary.quickStats.overallMemoryUsage', ['73317']),
            ('hardware.memorySize', ['206121951232']),
        ]),
        [Service()],
    ),
    (
        OrderedDict([
            ('summary.quickStats.overallMemoryUsage', ['73317']),
        ]),
        [],
    ),
])
def test_discover_esx_vsphere_hostsystem_mem_usage(section, discovered_service):
    assert list(discover_esx_vsphere_hostsystem_mem_usage(section)) == discovered_service


@pytest.mark.parametrize('section, check_results', [
    (
        OrderedDict([
            ('summary.quickStats.overallMemoryUsage', ['73317']),
            ('hardware.memorySize', ['206121951232']),
        ]),
        [
            Result(state=State.OK, summary='Usage: 37.30% - 71.6 GiB of 192 GiB'),
            Metric(
                'mem_used',
                76878446592.0,
                levels=(164897560985.6, 185509756108.80002),
                boundaries=(0.0, 206121951232.0),
            ),
            Metric('mem_total', 206121951232.0),
        ],
    ),
    (
        OrderedDict([
            ('summary.quickStats.overallMemoryUsage', ['73317']),
        ]),
        [],
    ),
    (
        OrderedDict([
            ('summary.quickStats.overallMemoryUsage', ['73317']),
            ('hardware.memorySize', ['broken']),
        ]),
        [],
    ),
    (
        OrderedDict([
            ('summary.quickStats.overallMemoryUsage', ['73317']),
            ('hardware.memorySize', []),
        ]),
        [],
    ),
])
def test_check_esx_vsphere_hostsystem_mem_usage(section, check_results):
    assert list(check_esx_vsphere_hostsystem_mem_usage(
        {'levels_upper': (80.0, 90.0)},
        section,
    )) == check_results
