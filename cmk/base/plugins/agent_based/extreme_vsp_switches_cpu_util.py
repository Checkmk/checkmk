#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .agent_based_api.v1 import get_value_store, register, Service, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.cpu_util import check_cpu_util
from .utils.netextreme import DETECT_NETEXTREME


@dataclass
class VSPSwitchCPUUtilInfo:
    cpu_util: float


def parse_vsp_switches_cpu_util(string_table: StringTable) -> VSPSwitchCPUUtilInfo | None:
    try:
        return VSPSwitchCPUUtilInfo(
            cpu_util=float(string_table[0][0]),
        )
    except IndexError:
        return None


register.snmp_section(
    name="extreme_vsp_switches_cpu_util",
    parse_function=parse_vsp_switches_cpu_util,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.85.10.1.1",
        oids=[
            "2",  # rcKhiSlotCpuCurrentUtil
        ],
    ),
    detect=DETECT_NETEXTREME,
)


def discover_vsp_switches_cpu_util(section: VSPSwitchCPUUtilInfo | None) -> DiscoveryResult:
    if section:
        yield Service(item=None)


def check_vsp_switches_cpu_util(
    params: Mapping[str, Any],
    section: VSPSwitchCPUUtilInfo | None,
) -> CheckResult:
    if not section:
        return

    yield from check_cpu_util(
        util=section.cpu_util,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


register.check_plugin(
    name="extreme_vsp_switches_cpu_util",
    service_name="VSP Switches CPU Utilization",
    discovery_function=discover_vsp_switches_cpu_util,
    check_function=check_vsp_switches_cpu_util,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
