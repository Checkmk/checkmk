#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from ipaddress import IPv4Address
from typing import Self

from cmk.base.plugins.agent_based.agent_based_api.v1 import register
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


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


register.agent_section(
    name="isc_dhcpd",
    parse_function=parse_isc_dhcpd,
)
