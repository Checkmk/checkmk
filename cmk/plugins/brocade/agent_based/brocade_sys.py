#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_value_store,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util

Section = Mapping[str, int]


def parse_brocade_sys(string_table: StringTable) -> Section | None:
    try:
        return {
            "cpu_util": int(string_table[0][0]),
            "mem_used_percent": int(string_table[0][1]),
        }
    except (IndexError, ValueError):
        return None


snmp_section_brocade_sys = SimpleSNMPSection(
    name="brocade_sys",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588.2.1.1"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1916.2.306"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1588.2.1.1.1.26",
        oids=["1", "6"],
    ),
    parse_function=parse_brocade_sys,
)


def discover_brocade_sys_mem(section: Section) -> DiscoveryResult:
    yield Service()


def check_brocade_sys_mem(params: Mapping[str, Any], section: Section) -> CheckResult:
    levels = params["levels"]
    yield from check_levels(
        section["mem_used_percent"],
        metric_name="mem_used_percent",
        levels_upper=("fixed", levels) if levels is not None else ("no_levels", None),
        render_func=render.percent,
    )


check_plugin_brocade_sys_mem = CheckPlugin(
    name="brocade_sys_mem",
    service_name="Memory",
    sections=["brocade_sys"],
    discovery_function=discover_brocade_sys_mem,
    check_function=check_brocade_sys_mem,
    check_ruleset_name="memory_relative",
    check_default_parameters={"levels": None},
)


def discover_brocade_sys(section: Section) -> DiscoveryResult:
    yield Service()


def check_brocade_sys(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_cpu_util(
        util=section["cpu_util"],
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_brocade_sys = CheckPlugin(
    name="brocade_sys",
    service_name="CPU utilization",
    discovery_function=discover_brocade_sys,
    check_function=check_brocade_sys,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={},
)
