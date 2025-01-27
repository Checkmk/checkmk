#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NamedTuple

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
from cmk.plugins.lib import megaraid


class StorcliPDisk(NamedTuple):
    state: str
    size: tuple[float, str]


Section = Mapping[str, StorcliPDisk]


def parse_storcli_pdisks(string_table: StringTable) -> Section:
    section = {}
    controller_num = 0
    separator_count = 0
    for line in string_table:
        if line[0].startswith("-----"):
            separator_count += 1
        elif separator_count == 2:
            eid_and_slot, device, state, _drivegroup, size, size_unit = line[:6]
            section["C%i.%s-%s" % (controller_num, eid_and_slot, device)] = StorcliPDisk(
                state=megaraid.expand_abbreviation(state),
                size=(float(size), size_unit),
            )
        if separator_count == 3:
            # each controller has 3 separators, reset count and continue
            separator_count = 0
            controller_num += 1

    return section


agent_section_storcli_pdisks = AgentSection(
    name="storcli_pdisks",
    parse_function=parse_storcli_pdisks,
)


def discover_storcli_pdisks(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_storcli_pdisks(
    item: str,
    params: Mapping[str, int],
    section: Section,
) -> CheckResult:
    if item not in section:
        return

    size = section[item].size
    infotext = f"Size: {size[0]} {size[1]}"

    diskstate = section[item].state
    infotext += ", Disk State: %s" % diskstate

    status = params.get(diskstate, 3)

    yield Result(state=State(status), summary=infotext)


check_plugin_storcli_pdisks = CheckPlugin(
    name="storcli_pdisks",
    service_name="RAID PDisk EID:Slot-Device %s",
    discovery_function=discover_storcli_pdisks,
    check_function=check_storcli_pdisks,
    check_default_parameters=megaraid.PDISKS_DEFAULTS,
    check_ruleset_name="storcli_pdisks",
)
