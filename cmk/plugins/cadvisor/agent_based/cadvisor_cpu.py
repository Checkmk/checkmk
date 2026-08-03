#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, float]


def parse_cadvisor_cpu(string_table: StringTable) -> Section:
    cpu_info = json.loads(string_table[0][0])
    parsed: dict[str, float] = {}
    for cpu_name, cpu_entries in cpu_info.items():
        if len(cpu_entries) != 1:
            continue
        try:
            parsed[cpu_name] = float(cpu_entries[0]["value"])
        except KeyError:
            continue
    return parsed


def discover_cadvisor_cpu(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_cadvisor_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    cpu_user = section["cpu_user"]
    cpu_system = section["cpu_system"]
    cpu_total = cpu_user + cpu_system

    yield Result(state=State.OK, summary=f"User: {render.percent(cpu_user)}")
    yield Metric("user", cpu_user)

    yield Result(state=State.OK, summary=f"System: {render.percent(cpu_system)}")
    yield Metric("system", cpu_system)

    util_levels = params.get("util")
    if util_levels is not None:
        warn, crit = util_levels
        yield from check_levels(
            cpu_total,
            metric_name="util",
            levels_upper=("fixed", (warn, crit)),
            render_func=render.percent,
            label="Total CPU",
        )
    else:
        yield Result(state=State.OK, summary=f"Total CPU: {render.percent(cpu_total)}")
        yield Metric("util", cpu_total)


agent_section_cadvisor_cpu = AgentSection(
    name="cadvisor_cpu",
    parse_function=parse_cadvisor_cpu,
)

check_plugin_cadvisor_cpu = CheckPlugin(
    name="cadvisor_cpu",
    service_name="CPU utilization",
    discovery_function=discover_cadvisor_cpu,
    check_function=check_cadvisor_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={},
)
