#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Note: this check is deprecated. It is superseeded by the new
# Check_MK HW/SW Inventory.


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def inventory_dmi_sysinfo(section: StringTable) -> DiscoveryResult:
    if len(section) > 0 and section[0] == ["System", "Information"]:
        yield Service()


def check_dmi_sysinfo(section: StringTable) -> CheckResult:
    if len(section) == 0 or section[0] != ["System", "Information"]:
        yield Result(state=State.UNKNOWN, summary="Invalid information")
        return
    data = {}
    for line_ in section:
        line = " ".join(line_)
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()

    yield Result(
        state=State.OK,
        summary="Manufacturer: %s, Product-Name: %s, Version: %s, S/N: %s"
        % (
            data.get("Manufacturer", "Unknown"),
            data.get("Product Name", "Unknown"),
            data.get("Version", "Unknown"),
            data.get("Serial Number", "Unknown"),
        ),
    )
    return


def parse_dmi_sysinfo(string_table: StringTable) -> StringTable:
    return string_table


agent_section_dmi_sysinfo = AgentSection(name="dmi_sysinfo", parse_function=parse_dmi_sysinfo)
check_plugin_dmi_sysinfo = CheckPlugin(
    name="dmi_sysinfo",
    service_name="DMI Sysinfo",
    discovery_function=inventory_dmi_sysinfo,
    check_function=check_dmi_sysinfo,
)
