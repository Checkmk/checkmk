#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import OrderedDict

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.vsphere.agent_based import esx_vsphere_counters_gpu as plugin


def test_discover_esx_vsphere_counters_gpu_utilization() -> None:
    value = list(
        plugin.discover_esx_vsphere_counters_gpu_utilization(
            OrderedDict(
                {
                    "gpu.mem.reserved": {"gpu1": [(["2219712", "2219712"], "kiloBytes")]},
                    "gpu.mem.total": {"gpu1": [(["23580672", "23580672"], "kiloBytes")]},
                    "gpu.mem.usage": {"gpu1": [(["941", "941"], "percent")]},
                    "gpu.mem.used": {"gpu1": [(["2219712", "2219712"], "kiloBytes")]},
                    "gpu.power.used": {"gpu1": [(["24", "24"], "watt")]},
                    "gpu.temperature": {"gpu1": [(["37", "37"], "celsius")]},
                    "gpu.utilization": {"gpu1": [(["42", "42"], "percent")]},
                }
            )
        )
    )
    expected = [Service(item="gpu1")]
    assert value == expected


def test_check_counters_gpu_utilization() -> None:
    value = list(
        plugin.check_esx_vsphere_counters_gpu_utilization(
            item="gpu1",
            params=plugin.GpuUtilizationParams(levels_upper=("fixed", (80.0, 90.0))),
            section=OrderedDict({"gpu.utilization": {"gpu1": [(["42", "42"], "percent")]}}),
        )
    )
    expected = [
        Result(state=State.OK, summary="Utilization: 42.00%"),
        Metric("esx_gpu_utilization", 42.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]
    assert value == expected


def test_check_counters_gpu_utilization_missing() -> None:
    value = list(
        plugin.check_esx_vsphere_counters_gpu_utilization(
            item="gpu1",
            params=plugin.GpuUtilizationParams(levels_upper=("fixed", (80.0, 90.0))),
            section=OrderedDict({}),
        )
    )
    expected = [Result(state=State.UNKNOWN, summary="Utilization is unknown.")]
    assert value == expected
