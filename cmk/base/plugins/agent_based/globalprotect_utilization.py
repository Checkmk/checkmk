#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import (
    all_of,
    check_levels,
    exists,
    register,
    render,
    Result,
    Service,
    SNMPTree,
    startswith,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class Section(NamedTuple):
    utilization: int
    max_tunnels: int
    active_tunnels: int


def parse_globalprotect_utilization(string_table: StringTable) -> Optional[Section]:
    if not string_table or len(string_table[0]) < 3:
        return None

    return Section(
        utilization=int(string_table[0][0]),
        max_tunnels=int(string_table[0][1]),
        active_tunnels=int(string_table[0][2]),
    )


register.snmp_section(
    name="globalprotect_utilization",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "Palo Alto"),
        exists(".1.3.6.1.4.1.25461.2.1.2.5.1.*"),
    ),
    parse_function=parse_globalprotect_utilization,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25461.2.1.2.5.1",
        oids=[
            "1",  # panGPGatewayUtilization::panGPGWUtilizationPct
            "2",  # panGPGatewayUtilization::panGPGWUtilizationMaxTunnels
            "3",  # panGPGatewayUtilization::panGPGWUtilizationActiveTunnels
        ],
    ),
)


def discover_globalprotect_utilization(section: Section) -> DiscoveryResult:
    yield Service()


def check_globalprotect_utilization(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_levels(
        value=section.utilization,
        levels_upper=params.get("utilization"),
        boundaries=(0.0, 100.0),
        metric_name="channel_utilization",
        render_func=render.percent,
        label="Utilization",
    )

    yield from check_levels(
        value=section.active_tunnels,
        levels_upper=params.get("active_tunnels"),
        boundaries=(0, section.max_tunnels),
        metric_name="active_sessions",
        label="Active sessions",
    )

    yield Result(state=State.OK, summary=f"Max sessions: {section.max_tunnels}")


register.check_plugin(
    name="globalprotect_utilization",
    service_name="GlobalProtect Gateway Utilization",
    discovery_function=discover_globalprotect_utilization,
    check_function=check_globalprotect_utilization,
    check_ruleset_name="globalprotect_utilization",
    check_default_parameters={},
)
