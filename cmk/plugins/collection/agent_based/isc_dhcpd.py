#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from ipaddress import IPv4Address
from typing import Self

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
from cmk.plugins.lib.dhcp_pools import check_dhcp_pools_levels


@dataclass(frozen=True, kw_only=True)
class PoolRange:
    start: IPv4Address
    end: IPv4Address

    @classmethod
    def from_strings(cls, start: str, end: str) -> Self:
        return cls(start=IPv4Address(start), end=IPv4Address(end))


@dataclass(frozen=True, kw_only=True)
class DhcpdSection:
    pids: Sequence[int]
    pools: Mapping[str, PoolRange]
    leases: Sequence[IPv4Address]


def parse_isc_dhcpd(
    string_table: StringTable,
) -> DhcpdSection:
    pids: list[int] = []
    pools: dict[str, PoolRange] = {}
    leases: list[IPv4Address] = []

    mode = None
    for line in string_table:
        if line[0] in ["[general]", "[pools]", "[leases]"]:
            mode = line[0][1:-1]

        elif mode == "general":
            if line[0] == "PID:":
                pids = list(map(int, line[1:]))

        elif mode == "pools":
            if "bootp" in line[0]:
                line = line[1:]
            start, end = line[0], line[1]
            item = f"{start}-{end}"
            pools[item] = PoolRange.from_strings(start=start, end=end)

        elif mode == "leases":
            leases.append(IPv4Address(line[0]))

    return DhcpdSection(pids=pids, pools=pools, leases=leases)


agent_section_isc_dhcpd = AgentSection(
    name="isc_dhcpd",
    parse_function=parse_isc_dhcpd,
)


def discovery_isc_dhcpd(section: DhcpdSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section.pools)


def check_isc_dhcpd(item: str, params: Mapping, section: DhcpdSection) -> CheckResult:
    if not section.pids:
        yield Result(state=State.CRIT, summary="DHCP Daemon not running")
    elif len(section.pids) > 1:
        yield Result(
            state=State.WARN,
            summary=f"DHCP Daemon running {len(section.pids)} times (PIDs: {', '.join(map(str, section.pids))})",
        )

    if not (ip_range := section.pools.get(item)):
        return

    num_leases = int(ip_range.end) - int(ip_range.start) + 1
    num_used = len(
        [lease_dec for lease_dec in section.leases if ip_range.start <= lease_dec <= ip_range.end]
    )

    yield from check_dhcp_pools_levels(num_leases - num_used, num_used, None, num_leases, params)


check_plugin_isc_dhcpd = CheckPlugin(
    name="isc_dhcpd",
    service_name="DHCP Pool %s",
    discovery_function=discovery_isc_dhcpd,
    check_function=check_isc_dhcpd,
    check_ruleset_name="win_dhcp_pools",
    check_default_parameters={"free_leases": (15.0, 5.0)},
)
