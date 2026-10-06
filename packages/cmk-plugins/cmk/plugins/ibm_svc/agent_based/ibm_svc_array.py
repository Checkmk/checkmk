#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.ibm_svc.lib import parse_ibm_svc_with_header


@dataclass(frozen=True)
class RaidArray:
    raid_status: str
    raid_level: str
    tier: str


Section = Mapping[str, RaidArray]

# Example output from agent:
# <<<ibm_svc_array:sep(58)>>>
# 27:SSD_mdisk27:online:1:POOL_0_V7000_RZ:372.1GB:online:raid1:1:256:generic_ssd
# 28:SSD_mdisk28:online:2:POOL_1_V7000_BRZ:372.1GB:online:raid1:1:256:generic_ssd
# 29:SSD_mdisk0:online:1:POOL_0_V7000_RZ:372.1GB:online:raid1:1:256:generic_ssd
# 30:SSD_mdisk1:online:2:POOL_1_V7000_BRZ:372.1GB:online:raid1:1:256:generic_ssd


def parse_ibm_svc_array(
    string_table: Sequence[Sequence[str]],
) -> Section:
    dflt_header = [
        "mdisk_id",
        "mdisk_name",
        "status",
        "mdisk_grp_id",
        "mdisk_grp_name",
        "capacity",
        "raid_status",
        "raid_level",
        "redundancy",
        "strip_size",
        "tier",
        "encrypt",
    ]
    parsed: dict[str, RaidArray] = {}
    for id_, rows in parse_ibm_svc_with_header(string_table, dflt_header).items():
        try:
            data = rows[0]
        except IndexError:
            continue
        parsed.setdefault(
            id_,
            RaidArray(
                raid_status=data["raid_status"],
                raid_level=data["raid_level"],
                tier=data["tier"],
            ),
        )
    return parsed


def check_ibm_svc_array(item: str, section: Section) -> CheckResult:
    if (array := section.get(item)) is None:
        return

    if array.raid_status == "online":
        state = State.OK
    elif array.raid_status in ("offline", "degraded"):
        state = State.CRIT
    else:
        state = State.WARN

    yield Result(
        state=state,
        summary=f"Status: {array.raid_status}, RAID Level: {array.raid_level}, Tier: {array.tier}",
    )


def discover_ibm_svc_array(
    section: Section,
) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_ibm_svc_array = AgentSection(
    name="ibm_svc_array",
    parse_function=parse_ibm_svc_array,
)


check_plugin_ibm_svc_array = CheckPlugin(
    name="ibm_svc_array",
    service_name="RAID Array %s",
    discovery_function=discover_ibm_svc_array,
    check_function=check_ibm_svc_array,
)
