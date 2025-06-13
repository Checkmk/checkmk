#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.f5_bigip import F5_BIGIP


@dataclass(frozen=True)
class PoolMember:
    port: str
    monitor_state: int
    monitor_status: int
    session_status: int
    node_name: str


@dataclass()
class Section:
    active_members: int
    defined_members: int
    members_info: list[PoolMember]


def parse_f5_bigip_pool(string_table: Sequence[StringTable]) -> Mapping[str, Section]:
    parsed: dict[str, Section] = {}
    processed_member_info = False
    for block in string_table:
        if not block:
            continue

        # Member information
        if len(block[0]) == 3 and processed_member_info:
            break

        if len(block[0]) == 3:
            for line in block:
                parsed.setdefault(
                    line[0], Section(active_members=0, defined_members=0, members_info=[])
                )
                parsed[line[0]].active_members += int(line[1])
                parsed[line[0]].defined_members += int(line[2])
            processed_member_info = True

        # Status information
        elif len(block[0]) == 6:
            for line in block:
                section = parsed.get(line[0])
                if section:
                    parsed[line[0]].members_info.append(
                        PoolMember(
                            port=line[1],
                            monitor_state=int(line[2]),
                            monitor_status=int(line[3]),
                            session_status=int(line[4]),
                            node_name=line[5],
                        )
                    )

    return parsed


def inventory_f5_bigip_pool(section: Mapping[str, Section]) -> DiscoveryResult:
    for item in section:
        if item != "":
            yield Service(item=item)


def f5_bigip_pool_get_down_members(members_info: list[PoolMember]) -> str:
    up_states = (
        4,  # up
        28,  # fqdnUp (https://my.f5.com/manage/s/article/K57299401)
    )
    disabled_states = (
        2,  # addrdisabled
        3,  # servdisabled
        4,  # disabled
        5,  # forceddisabled
    )
    down_list = []
    for member in members_info:
        if (
            member.monitor_state not in up_states
            or member.monitor_status not in up_states
            or member.session_status in disabled_states
        ):
            if re.match(r"\/\S*\/\S*", member.node_name):
                host = member.node_name.split("/")[2]
            else:
                host = member.node_name
            down_list.append(host + ":" + member.port)

    return ", ".join(down_list)


def check_f5_bigip_pool(
    item: str, params: Mapping[str, LevelsT], section: Mapping[str, Section]
) -> CheckResult:
    pool = section.get(item)
    if not pool:
        return

    if pool.active_members == pool.defined_members:
        yield Result(state=State.OK, summary=f"Members up: {pool.active_members}")
    else:
        yield from check_levels(
            value=pool.active_members,
            levels_lower=params["levels_lower"],
            render_func=str,
            label="Members up",
        )

    yield Result(state=State.OK, summary=f"Members total: {pool.defined_members}")

    if pool.active_members < pool.defined_members:
        down_list = f5_bigip_pool_get_down_members(pool.members_info)
        if down_list:
            yield Result(state=State.OK, summary=f"down/disabled nodes: {down_list}")


snmp_section_f5_bigip_pool = SNMPSection(
    name="f5_bigip_pool",
    detect=F5_BIGIP,
    parse_function=parse_f5_bigip_pool,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.2.5.1.2.1",
            oids=[
                "1",  # F5-BIGIP-LOCAL-MIB::ltmPoolName
                "8",  # F5-BIGIP-LOCAL-MIB::ltmPoolActiveMemberCnt
                "23",  # F5-BIGIP-LOCAL-MIB::ltmPoolMemberCnt
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.2.5.3.2.1",
            oids=[
                "1",  # F5-BIGIP-LOCAL-MIB::ltmPoolMemberPoolName
                "4",  # F5-BIGIP-LOCAL-MIB::ltmPoolMemberPort
                "10",  # F5-BIGIP-LOCAL-MIB::ltmPoolMemberMonitorState (ltmNodeAddrMonitorState)
                "11",  # F5-BIGIP-LOCAL-MIB::ltmPoolMemberMonitorStatus (ltmNodeAddrMonitorStatus)
                "13",  # F5-BIGIP-LOCAL-MIB::ltmPoolMemberSessionStatus
                "19",  # F5-BIGIP-LOCAL-MIB::ltmPoolMemberNodeName
            ],
        ),
    ],
)

check_plugin_f5_bigip_pool = CheckPlugin(
    name="f5_bigip_pool",
    service_name="Load Balancing Pool %s",
    discovery_function=inventory_f5_bigip_pool,
    check_function=check_f5_bigip_pool,
    check_ruleset_name="f5_pools",
    check_default_parameters={"levels_lower": ("fixed", (2, 1))},
)
