#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# 1  Raid Set # 00        3 2250.5GB    0.0GB 123                Normal
# ( # Name Disks TotalCap  FreeCap DiskChannels State )


from collections.abc import Mapping
from typing import Any

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


def inventory_arc_raid_status(section: StringTable) -> DiscoveryResult:
    yield from [Service(item=x[0], parameters={"n_disks": int(x[-5])}) for x in section]


def check_arc_raid_status(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for line in section:
        if line[0] == item:
            raid_state = line[-1]
            match raid_state:
                case "Checking" | "Normal":
                    state = State.OK
                case "Rebuilding":
                    state = State.WARN
                case "Degrade" | "Incompleted":
                    state = State.CRIT
                case _other:
                    state = State.CRIT

            yield Result(state=state, summary=raid_state.title())

            # Check the number of disks
            i_disks = params["n_disks"]
            c_disks = int(line[-5])
            if i_disks != c_disks:
                yield Result(
                    state=State.CRIT,
                    summary=f"Number of disks has changed from {i_disks} to {c_disks}",
                )

            return


def parse_arc_raid_status(string_table: StringTable) -> StringTable:
    return string_table


agent_section_arc_raid_status = AgentSection(
    name="arc_raid_status",
    parse_function=parse_arc_raid_status,
)


check_plugin_arc_raid_status = CheckPlugin(
    name="arc_raid_status",
    service_name="Raid Array #%s",
    discovery_function=inventory_arc_raid_status,
    check_function=check_arc_raid_status,
    check_default_parameters={},
)
