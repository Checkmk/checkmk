#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary output of special agent agent_ucs_bladecenter (separator is <TAB> and means tabulator):
#
# <<<ucs_c_rack_server_util:sep(9)>>>
# serverUtilization<TAB>dn sys/rack-unit-1/utilization<TAB>overallUtilization 0<TAB>cpuUtilization 0<TAB>memoryUtilization 0<TAB>ioUtilization 0
# serverUtilization<TAB>dn sys/rack-unit-2/utilization<TAB>overallUtilization 90<TAB>cpuUtilization 90<TAB>memoryUtilization 90<TAB>ioUtilization 90
#
# The format of the XML API v2.0 raw output provided via the agent is not documented.
# The description about the meaning of the XML attributes is described in the corresponding
# section of the GUI Configuration Guide. The units of overallUtilization, cpuUtilization,
# memoryUtilization and ioUtilization are percentages.
# https://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/c/sw/gui/config/guide/3_1/b_Cisco_UCS_C-series_GUI_Configuration_Guide_31/b_Cisco_UCS_C-series_GUI_Configuration_Guide_31_chapter_0101.pdf

import time
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Service,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util


@dataclass(frozen=True)
class RackUtilizations:
    overall: float | None = None
    cpu: float | None = None
    memory: float | None = None
    io: float | None = None


Section = Mapping[str, RackUtilizations]


def parse_ucs_c_rack_server_util(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, float]] = {}
    # The element count of info lines is under our control (agent output) and
    # ensured to have expected length. It is ensured that elements contain a
    # string. Handles invalid values provided by the XML API which cannot be
    # casted by setting corresponding values to None.
    for _, dn, overall_util, cpu_util, memory_util, pci_io_util in string_table:
        rack_name = (
            dn.replace("dn ", "")
            .replace("sys/", "")
            .replace("rack-unit-", "Rack unit ")
            .replace("/utilization", "")
        )

        for ds_key, parsed_key, ds in (
            ("overallUtilization", "overall", overall_util),
            ("cpuUtilization", "cpu", cpu_util),
            ("memoryUtilization", "memory", memory_util),
            ("ioUtilization", "io", pci_io_util),
        ):
            try:
                value = float(ds.replace(ds_key + " ", ""))
            except ValueError:
                continue
            parsed.setdefault(rack_name, {})[parsed_key] = value

    return {
        rack_name: RackUtilizations(**utilizations) for rack_name, utilizations in parsed.items()
    }


agent_section_ucs_c_rack_server_util = AgentSection(
    name="ucs_c_rack_server_util",
    parse_function=parse_ucs_c_rack_server_util,
)


def discover_ucs_c_rack_server_util(section: Section) -> DiscoveryResult:
    yield from (Service(item=rack_name) for rack_name in section)


def check_ucs_c_rack_server_util(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if not (rack_utils := section.get(item)):
        return
    if (overall_util := rack_utils.overall) is None:
        return
    yield from check_levels_v1(
        overall_util,
        levels_upper=params["upper_levels"],
        metric_name="overall_util",
        render_func=render.percent,
    )


check_plugin_ucs_c_rack_server_util = CheckPlugin(
    name="ucs_c_rack_server_util",
    service_name="Overall Utilization %s",
    discovery_function=discover_ucs_c_rack_server_util,
    check_function=check_ucs_c_rack_server_util,
    check_ruleset_name="overall_utilization_multiitem",
    check_default_parameters={"upper_levels": (90.0, 95.0)},
)


def check_ucs_c_rack_server_util_cpu_(
    *,
    item: str,
    params: Mapping[str, Any],
    section: Section,
    value_store: MutableMapping[str, Any],
    timestamp: float,
) -> CheckResult:
    if not (rack_utils := section.get(item)):
        return
    if (cpu_util := rack_utils.cpu) is None:
        return
    yield from check_cpu_util(
        util=cpu_util,
        params=params,
        value_store=value_store,
        this_time=timestamp,
    )


def check_ucs_c_rack_server_util_cpu(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    yield from check_ucs_c_rack_server_util_cpu_(
        item=item,
        params=params,
        section=section,
        value_store=get_value_store(),
        timestamp=time.time(),
    )


check_plugin_ucs_c_rack_server_util_cpu = CheckPlugin(
    name="ucs_c_rack_server_util_cpu",
    sections=["ucs_c_rack_server_util"],
    service_name="CPU Utilization %s",
    discovery_function=discover_ucs_c_rack_server_util,
    check_function=check_ucs_c_rack_server_util_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)


def check_ucs_c_rack_server_util_pci_io(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if not (rack_utils := section.get(item)):
        return
    if (io_util := rack_utils.io) is None:
        return
    yield from check_levels_v1(
        io_util,
        levels_upper=params["upper_levels"],
        metric_name="pci_io_util",
        render_func=render.percent,
    )


check_plugin_ucs_c_rack_server_util_pci_io = CheckPlugin(
    name="ucs_c_rack_server_util_pci_io",
    sections=["ucs_c_rack_server_util"],
    service_name="PCI IO Utilization %s",
    discovery_function=discover_ucs_c_rack_server_util,
    check_function=check_ucs_c_rack_server_util_pci_io,
    check_ruleset_name="pci_io_utilization_multiitem",
    check_default_parameters={"upper_levels": (90.0, 95.0)},
)


def check_ucs_c_rack_server_util_mem(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if not (rack_utils := section.get(item)):
        return
    if (memory_util := rack_utils.memory) is None:
        return
    yield from check_levels_v1(
        memory_util,
        levels_upper=params["upper_levels"],
        metric_name="memory_util",
        render_func=render.percent,
    )


check_plugin_ucs_c_rack_server_util_mem = CheckPlugin(
    name="ucs_c_rack_server_util_mem",
    sections=["ucs_c_rack_server_util"],
    service_name="Memory Utilization %s",
    discovery_function=discover_ucs_c_rack_server_util,
    check_function=check_ucs_c_rack_server_util_mem,
    check_ruleset_name="memory_utilization_multiitem",
    check_default_parameters={"upper_levels": (90.0, 95.0)},
)
