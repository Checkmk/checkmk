#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.pulse_secure import lib as pulse_secure

Section = Mapping[str, int]

_METRIC_KEYS = ("mem_used_percent", "swap_used_percent")


class PulseSecureMemUtilParams(TypedDict, total=False):
    mem_used_percent: tuple[float, float]
    swap_used_percent: tuple[float, float]


def parse_pulse_secure_mem(string_table: StringTable) -> Section | None:
    return pulse_secure.parse_pulse_secure(string_table, *_METRIC_KEYS)


def discover_pulse_secure_mem_util(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_pulse_secure_mem(params: PulseSecureMemUtilParams, section: Section) -> CheckResult:
    if not section:
        return

    if "mem_used_percent" in section:
        yield from check_levels(
            section["mem_used_percent"],
            levels_upper=params.get("mem_used_percent"),
            metric_name="mem_used_percent",
            render_func=render.percent,
            label="RAM used",
        )
    if "swap_used_percent" in section:
        yield from check_levels(
            section["swap_used_percent"],
            levels_upper=params.get("swap_used_percent"),
            metric_name="swap_used_percent",
            render_func=render.percent,
            label="Swap used",
        )


snmp_section_pulse_secure_mem_util = SimpleSNMPSection(
    name="pulse_secure_mem_util",
    detect=pulse_secure.DETECT_PULSE_SECURE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12532",
        oids=["11", "24"],
    ),
    parse_function=parse_pulse_secure_mem,
)


check_plugin_pulse_secure_mem_util = CheckPlugin(
    name="pulse_secure_mem_util",
    service_name="Pulse Secure IVE memory utilization",
    discovery_function=discover_pulse_secure_mem_util,
    check_function=check_pulse_secure_mem,
    check_ruleset_name="pulse_secure_mem_util",
    check_default_parameters={
        "mem_used_percent": (90, 95),
        "swap_used_percent": (5, 101),
    },
)
