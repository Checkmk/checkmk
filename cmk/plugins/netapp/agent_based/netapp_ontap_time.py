#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    LevelsT,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.netapp import models

Section = Mapping[str, models.NodeModel]


def discover_netapp_ontap_time(section: Section) -> DiscoveryResult:
    for node_name, model in section.items():
        if model.date is not None:
            yield Service(item=node_name)


class Params(TypedDict):
    upper_levels: LevelsT[float]


def check_netapp_ontap_time(item: str, params: Params, section: Section) -> CheckResult:
    if (node_info := section.get(item)) is None:
        return

    if node_info.date is None:
        raise IgnoreResultsError("Node provided no time information.")

    node_timestamp = node_info.date.timestamp()
    system_timestamp = time.time()
    offset = abs(system_timestamp - node_timestamp)

    yield Result(state=State.OK, summary=f"Node time: {node_info.date}")

    yield from check_levels(
        offset,
        levels_upper=params.get("upper_levels"),
        metric_name="time_offset",
        render_func=render.timespan,
        label="Absolute offset",
    )


check_plugin_netapp_ontap_time = CheckPlugin(
    name="netapp_ontap_time",
    service_name="System time Node %s",
    sections=["netapp_ontap_node"],
    discovery_function=discover_netapp_ontap_time,
    check_function=check_netapp_ontap_time,
    check_ruleset_name="netapp_system_time_offset",
    check_default_parameters={"upper_levels": ("fixed", (30.0, 60.0))},
)
