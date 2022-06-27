#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.api.agent_based.utils import GetRateError
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.cpu_utilization_os import check_cpu_utilization_os
from cmk.base.plugins.agent_based.utils.container_cgroupv2 import parse_cpu
from cmk.base.plugins.agent_based.utils.cpu_utilization_os import SectionCpuUtilizationOs

AGENT_OUTPUT = [
    ["uptime", "200716.86", "651734.60"],
    ["num_cpus", "8"],
    ["usage_usec", "863372"],
    ["user_usec", "610384"],
    ["system_usec", "252988"],
    ["nr_periods", "0"],
    ["nr_throttled", "0"],
    ["throttled_usec", "0"],
]

AGENT_OUTPUT_0 = [
    ["uptime", "8028.51", "8028.51"],
    ["num_cpus", "2"],
    ["usage_usec", "1471001364"],
    ["user_usec", "564881022"],
    ["system_usec", "906120342"],
    ["nr_periods", "0"],
    ["nr_throttled", "0"],
    ["throttled_usec", "0"],
]

AGENT_OUTPUT_1 = [
    ["uptime", "8037.18", "8037.18"],
    ["num_cpus", "2"],
    ["usage_usec", "1480005388"],
    ["user_usec", "571438204"],
    ["system_usec", "908567184"],
    ["nr_periods", "0"],
    ["nr_throttled", "0"],
    ["throttled_usec", "0"],
]


def test_parse_cpu_cgroupv2() -> None:
    assert parse_cpu(AGENT_OUTPUT) == SectionCpuUtilizationOs(
        time_base=200716.86,
        num_cpus=8,
        time_cpu=0.863372,
    )


def test_check_cpu_cgroupv2() -> None:
    with pytest.raises(GetRateError):
        # no rate metrics yet
        _ = list(check_cpu_utilization_os({}, parse_cpu(AGENT_OUTPUT_0)))
    result = check_cpu_utilization_os({}, parse_cpu(AGENT_OUTPUT_1))
    assert list(result) == [
        Result(state=State.OK, summary="Total CPU: 103.85%"),
        Metric("util", 103.8526412918108, boundaries=(0.0, None)),
    ]
