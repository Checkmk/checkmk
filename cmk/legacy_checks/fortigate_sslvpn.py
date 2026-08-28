#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fortinet.lib import DETECT_FORTIGATE


@dataclass(frozen=True)
class VPNDomain:
    state: str
    users: int
    web_sessions: int
    tunnels: int
    tunnels_max: int


Section = Mapping[str, VPNDomain]


def parse_fortigate_sslvpn(string_table: Sequence[StringTable]) -> Section:
    return {
        domain_name[0]: VPNDomain(
            state=domain_info[0],
            users=int(domain_info[1]),
            web_sessions=int(domain_info[2]),
            tunnels=int(domain_info[3]),
            tunnels_max=int(domain_info[4]),
        )
        for domain_name, domain_info in zip(string_table[0], string_table[1])
    }


def discover_fortigate_sslvpn(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_fortigate_sslvpn(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    fn_bool_state = {"1": "disabled", "2": "enabled"}
    yield Result(state=State.OK, summary=fn_bool_state[data.state])

    yield from check_levels_v1(
        data.users, metric_name="active_vpn_users", render_func=str, label="Users"
    )

    yield from check_levels_v1(
        data.web_sessions,
        metric_name="active_vpn_websessions",
        render_func=str,
        label="Web sessions",
    )

    yield from check_levels_v1(
        data.tunnels,
        metric_name="active_vpn_tunnels",
        levels_upper=params.get("tunnel_levels"),
        render_func=str,
        label="Tunnels",
        boundaries=(0, data.tunnels_max),
    )


snmp_section_fortigate_sslvpn = SNMPSection(
    name="fortigate_sslvpn",
    detect=DETECT_FORTIGATE,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.3.2.1.1",
            oids=["2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.12.2.3.1",
            oids=["1", "2", "4", "6", "7"],
        ),
    ],
    parse_function=parse_fortigate_sslvpn,
)


check_plugin_fortigate_sslvpn = CheckPlugin(
    name="fortigate_sslvpn",
    service_name="VPN SSL %s",
    discovery_function=discover_fortigate_sslvpn,
    check_function=check_fortigate_sslvpn,
    check_ruleset_name="fortigate_sslvpn",
    check_default_parameters={},
)
