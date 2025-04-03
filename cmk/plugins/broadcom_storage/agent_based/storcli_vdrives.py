#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.plugins.broadcom_storage.lib.megaraid import expand_abbreviation, LDISKS_DEFAULTS


class StorcliVDrive(NamedTuple):
    raid_type: str
    state: str
    access: str
    consistent: bool


StorcliVDrivesSection = Mapping[str, StorcliVDrive]


def parse_storcli_vdrives(string_table: StringTable) -> StorcliVDrivesSection:
    section: dict[str, StorcliVDrive] = {}

    controller_num = 0
    separator_count = 0

    for line in string_table:
        if line[0].startswith("-----"):
            separator_count += 1
        elif separator_count == 2:
            dg_vd, raid_type, rawstate, access, consistent = line[:5]
            section[f"C{controller_num}.{dg_vd}"] = StorcliVDrive(
                raid_type=raid_type,
                state=expand_abbreviation(rawstate),
                access=access,
                consistent=consistent == "Yes",
            )

        if separator_count == 3:
            # each controller has 3 separators, reset count and continue
            separator_count = 0
            controller_num += 1

    return section


agent_section_storcli_vdrives = AgentSection(
    name="storcli_vdrives",
    parse_function=parse_storcli_vdrives,
)


def discover_storcli_vdrives(section: StorcliVDrivesSection) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_storcli_vdrives(
    item: str,
    params: Mapping[str, int],
    section: StorcliVDrivesSection,
) -> CheckResult:
    if (drive := section.get(item)) is None:
        return

    yield Result(state=State.OK, summary=f"Raid type is {drive.raid_type}")
    yield Result(state=State.OK, summary=f"Access: {drive.access}")

    if not drive.consistent:
        yield Result(state=State.WARN, summary="Drive is not consistent")
    else:
        yield Result(state=State.OK, summary="Drive is consistent")

    summary = "State is %s" % drive.state

    if (raw_state := params.get(drive.state)) is None:
        state = State.UNKNOWN
        summary += " (unknown[%s])" % drive.state
    else:
        state = State(raw_state)

    yield Result(state=state, summary=summary)


check_plugin_storcli_vdrives = CheckPlugin(
    name="storcli_vdrives",
    service_name="RAID Virtual Drive %s",
    discovery_function=discover_storcli_vdrives,
    check_function=check_storcli_vdrives,
    check_default_parameters=LDISKS_DEFAULTS,
    check_ruleset_name="storcli_vdrives",
)
