#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.vsphere.lib.esx_vsphere import average_valid_samples, Section

# Example output:
# <<<esx_vsphere_counters:sep(124)>>>
# gpu.mem.reserved|gpu-1|318976|kiloBytes
# gpu.mem.total|gpu-1|23580672|kiloBytes
# gpu.mem.usage|gpu-1|135|percent
# gpu.mem.used|gpu-1|318976|kiloBytes
# gpu.power.used|gpu-1|21|watt
# gpu.temperature|gpu-1|35|celsius
# gpu.utilization|gpu-1|42|percent
#
# The vSphere performance API reports percent counters as fixed point integers
# in hundredths of a percent (e.g. 2067 means 20.67%); see the counter
# reference of vim.PerformanceManager. The gpu.mem.usage sample above confirms
# this: 135 corresponds to 318976/23580672 kB = 1.35%.


def discover_esx_vsphere_counters_gpu_utilization(section: Section) -> DiscoveryResult:
    yield from (Service(item=gpu_id) for gpu_id in section.get("gpu.utilization", {}))


class GpuUtilizationParams(TypedDict):
    levels_upper: FixedLevelsT[float]


def check_esx_vsphere_counters_gpu_utilization(
    item: str, params: GpuUtilizationParams, section: Section
) -> CheckResult:
    gpu_data = section.get("gpu.utilization", {}).get(item)
    if not gpu_data or gpu_data[0][1] != "percent":
        yield Result(state=State.UNKNOWN, summary="Utilization is unknown.")
        return

    # average_valid_samples returns None when all samples for the interval are
    # unavailable (-1); treat that as unknown rather than reporting -1%.
    raw_utilization = average_valid_samples(gpu_data[0][0])
    if raw_utilization is None:
        yield Result(state=State.UNKNOWN, summary="Utilization is unknown.")
        return

    yield from check_levels(
        # percent counters are reported in hundredths of a percent (see above)
        raw_utilization / 100.0,
        levels_upper=params["levels_upper"],
        render_func=render.percent,
        metric_name="esx_gpu_utilization",
        label="Utilization",
        boundaries=(0.0, 100.0),
    )


check_plugin_esx_vsphere_counters_gpu_utilization = CheckPlugin(
    name="esx_vsphere_counters_gpu_utilization",
    sections=["esx_vsphere_counters"],
    service_name="GPU Utilization %s",
    discovery_function=discover_esx_vsphere_counters_gpu_utilization,
    check_function=check_esx_vsphere_counters_gpu_utilization,
    check_ruleset_name="esx_vsphere_counters_gpu_utilization",
    check_default_parameters=GpuUtilizationParams(levels_upper=("fixed", (80.0, 90.0))),
)
