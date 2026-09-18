#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Service,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util

# Example output from agent:
# <<<vms_cpu>>>
# 1 99.17 0.54 0.18 0.00

Section = dict[str, int | float]


def parse_vms_cpu(string_table: StringTable) -> Section:
    parsed: Section = {}
    try:
        parsed["num_cpus"] = int(string_table[0][0])
        for i, key in enumerate(("idle", "user", "wait_interrupt", "wait_npsync"), 1):
            parsed[key] = float(string_table[0][i]) / parsed["num_cpus"]
    except IndexError, ValueError:
        return {}

    return parsed


def discover_vms_cpu(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vms_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    user = section["user"]
    wait = section["wait_interrupt"] + section["wait_npsync"]
    util = 100.0 - section["idle"]
    system = util - user - wait

    yield from check_levels(user, metric_name="user", render_func=render.percent, label="User")
    yield from check_levels(
        system, metric_name="system", render_func=render.percent, label="System"
    )
    raw_iowait: tuple[float, float] | None = params.get("iowait")

    yield from check_levels(
        wait,
        metric_name="wait",
        levels_upper=("fixed", raw_iowait) if raw_iowait is not None else None,
        render_func=render.percent,
        label="Wait",
    )

    yield from check_cpu_util(
        util=util,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
        perf_max=100,
    )

    num_cpus = section["num_cpus"]
    unit = "CPU" if num_cpus == 1 else "CPUs"
    yield from check_levels(
        num_cpus,
        metric_name="cpu_entitlement",
        render_func=lambda x: f"{int(x)} {unit}",
        label="100% corresponding to",
    )


agent_section_vms_cpu = AgentSection(
    name="vms_cpu",
    parse_function=parse_vms_cpu,
)

check_plugin_vms_cpu = CheckPlugin(
    name="vms_cpu",
    service_name="CPU utilization",
    discovery_function=discover_vms_cpu,
    check_function=check_vms_cpu,
    check_ruleset_name="cpu_iowait",
    check_default_parameters={},
)
