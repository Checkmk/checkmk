#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output of agent:
# <<<fsc-ipmi-mem-status>>>
# 0 DIMM-1A 01
# 1 DIMM-1B 03
# 2 DIMM-2A 00
# 3 DIMM-2B 00
#
# Available state levels:
# 00 = Empty slot
# 01 = OK, running
# 02 = reserved
# 03 = Error (module has encountered errors, but is still in use)
# 04 = Fail (module has encountered errors and is therefore disabled)
# 05 = Prefail (module exceeded the correctable errors threshold)


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}

fsc_ipmi_mem_status_levels = [
    # Status Code, Label
    (0, "Empty slot"),
    (0, "Running"),
    (0, "Reserved"),
    (2, "Error (module has encountered errors, but is still in use)"),
    (2, "Fail (module has encountered errors and is therefore disabled)"),
    (2, "Prefail (module exceeded the correctable errors threshold)"),
]


def inventory_fsc_ipmi_mem_status(info):
    # Skip all lines which have
    # a) An error (Begin with "E")
    # b) Don't have a status (line[2])
    # c) Don't have a module
    return [
        (line[1], None) for line in info if line[0] != "E" and len(line) > 2 and line[2] != "00"
    ]


def check_fsc_ipmi_mem_status(name, _no_params, info):
    for line in info:
        if line[0] == "E":
            return (3, "Error in agent plug-in output (%s)" % " ".join(line[1:]))
        if line[1] == name:
            return fsc_ipmi_mem_status_levels[int(line[2])]

    return (3, "item %s not found" % name)


def parse_fsc_ipmi_mem_status(string_table: StringTable) -> StringTable:
    return string_table


check_info["fsc_ipmi_mem_status"] = LegacyCheckDefinition(
    name="fsc_ipmi_mem_status",
    parse_function=parse_fsc_ipmi_mem_status,
    service_name="IPMI Memory status %s",
    discovery_function=inventory_fsc_ipmi_mem_status,
    check_function=check_fsc_ipmi_mem_status,
)
