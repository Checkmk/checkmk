#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Defined by customer, see SUP-1020

from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

Section = Mapping[str, Mapping[str, float]]


class HuaweiWlcDevsLevelsParams(TypedDict, total=False):
    levels: tuple[float, float]


def parse_huawei_wlc_devs(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, float]] = {}
    for name, cpu_perc, mem_perc in string_table:
        if name:
            parsed[name] = {
                "cpu_percent": float(cpu_perc),
                "mem_used_percent": float(mem_perc),
            }
    return parsed


snmp_section_huawei_wlc_devs = SimpleSNMPSection(
    name="huawei_wlc_devs",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2011.2.240.17"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.5.25.31.1.1",
        oids=["2.1.13", "1.1.5", "1.1.7"],
    ),
    parse_function=parse_huawei_wlc_devs,
)


def discovery_huawei_wlc_devs_mem(section: Section) -> DiscoveryResult:
    for name, dev in section.items():
        if dev.get("mem_used_percent") is not None:
            yield Service(item=name)


def check_huawei_wlc_devs_mem(
    item: str, params: HuaweiWlcDevsLevelsParams, section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return

    yield from check_levels(
        data["mem_used_percent"],
        levels_upper=params.get("levels"),
        metric_name="mem_used_percent",
        render_func=render.percent,
        label="Used",
    )


check_plugin_huawei_wlc_devs_mem = CheckPlugin(
    name="huawei_wlc_devs_mem",
    service_name="Device %s Memory",
    sections=["huawei_wlc_devs"],
    discovery_function=discovery_huawei_wlc_devs_mem,
    check_function=check_huawei_wlc_devs_mem,
    check_default_parameters={"levels": (80.0, 90.0)},
)


def discovery_huawei_wlc_devs_cpu(section: Section) -> DiscoveryResult:
    for name, dev in section.items():
        if dev.get("cpu_percent") is not None:
            yield Service(item=name)


def check_huawei_wlc_devs_cpu(
    item: str, params: HuaweiWlcDevsLevelsParams, section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return

    yield from check_levels(
        data["cpu_percent"],
        levels_upper=params.get("levels"),
        metric_name="cpu_percent",
        render_func=render.percent,
        label="Usage",
    )


check_plugin_huawei_wlc_devs_cpu = CheckPlugin(
    name="huawei_wlc_devs_cpu",
    service_name="Device %s CPU",
    sections=["huawei_wlc_devs"],
    discovery_function=discovery_huawei_wlc_devs_cpu,
    check_function=check_huawei_wlc_devs_cpu,
    check_default_parameters={"levels": (80.0, 90.0)},
)
