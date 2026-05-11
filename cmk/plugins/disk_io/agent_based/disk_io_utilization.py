#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Service,
)


class Params(TypedDict):
    upper_levels: LevelsT[float]


def check_disk_io_utilization(params: Params, section: float) -> CheckResult:
    yield from check_levels(
        section,
        label="Total Disk IO Utilization",
        metric_name="disk_io_utilization",
        levels_upper=params["upper_levels"],
        render_func=render.percent,
    )


def discover_disk_io_utilization(section: float) -> DiscoveryResult:
    yield Service()


check_plugin_disk_io_utilization = CheckPlugin(
    name="disk_io_utilization",
    service_name="Disk IO Utilization",
    discovery_function=discover_disk_io_utilization,
    check_function=check_disk_io_utilization,
    check_default_parameters=Params(upper_levels=("fixed", (80.0, 90.0))),
    check_ruleset_name="generic_percentage_value",
)
