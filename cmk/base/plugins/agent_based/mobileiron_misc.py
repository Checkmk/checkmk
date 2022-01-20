#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    register,
    render,
    Result,
    Service,
    State,
)

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.mobileiron import Section


def check_mobileiron_misc(params: Mapping[str, Any], section: Section) -> CheckResult:

    if availableCapacity := section.availableCapacity:
        yield from check_levels(
            label="Available capacity",
            value=availableCapacity,
            levels_upper=params.get("available_capacity"),
            metric_name="capacity_perc",
            render_func=render.percent,
        )

    yield Result(
        state=State.OK if section.uptime else State.UNKNOWN,
        summary=f"Uptime: {render.timespan(section.uptime) if section.uptime else None}",
    )

    yield Result(
        state=State.OK,
        summary=f"IP address: {section.ipAddress}",
    )


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


register.check_plugin(
    name="mobileiron_misc",
    sections=["mobileiron_section"],
    service_name="Mobileiron miscellaneous",
    discovery_function=discover_single,
    check_function=check_mobileiron_misc,
    check_ruleset_name="mobileiron_misc",
    check_default_parameters={"available_capacity": (70.0, 90.0)},
)
