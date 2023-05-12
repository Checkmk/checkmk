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

from collections.abc import Mapping
from dataclasses import dataclass

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable


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


register.agent_section(
    name="ucs_c_rack_server_util",
    parse_function=parse_ucs_c_rack_server_util,
)
