#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.palo_alto import DETECT_PALO_ALTO

LEVEL_TYPE = tuple[float, float] | None


@dataclass(frozen=True)
class Section:
    num_users: int
    max_users: int


def parse(string_table: StringTable) -> Section | None:
    return (
        Section(num_users=int(string_table[0][1]), max_users=int(string_table[0][0]))
        if string_table
        else None
    )


snmp_section_palo_alto_users = SimpleSNMPSection(
    name="palo_alto_users",
    parse_function=parse,
    detect=DETECT_PALO_ALTO,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25461.2.1.2.5.1",
        oids=[
            "2.0",  # panGPGWUtilizationMaxTunnels
            "3.0",  # panGPGWUtilizationActiveTunnels
        ],
    ),
)


def discover(section: Section) -> DiscoveryResult:
    yield Service()


def _abs_and_rel_levels(levels: tuple[str, LEVEL_TYPE]) -> tuple[LEVEL_TYPE, LEVEL_TYPE]:
    match levels:
        case "ignore":
            return None, None
        case ("abs_user", thresholds):
            return thresholds, None
        case ("perc_user", thresholds):
            return None, thresholds
    return None, None


def check(params: Mapping[str, Any], section: Section) -> CheckResult:
    user_perc = section.num_users / section.max_users * 100

    yield Result(
        state=State.OK,
        summary=f"Number of logged in users: "
        f"{render.percent(user_perc)} - {section.num_users} of {section.max_users}",
    )

    abs_levels, perc_levels = _abs_and_rel_levels(params["levels"])

    yield from check_levels_v1(
        section.num_users,
        levels_upper=abs_levels,
        metric_name="num_user",
        render_func=str,
        label="Absolute number of users",
        notice_only=True,
    )
    yield from check_levels_v1(
        user_perc,
        levels_upper=perc_levels,
        render_func=render.percent,
        label="Relative number of users",
        notice_only=True,
    )

    yield Metric("max_user", section.max_users)


def cluster_check(
    params: Mapping[str, Any],
    section: Mapping[str, Section | None],
) -> CheckResult:
    yield from check(
        params,
        Section(
            num_users=sum(
                node_section.num_users if node_section else 0 for node_section in section.values()
            ),
            max_users=sum(
                node_section.max_users if node_section else 0 for node_section in section.values()
            ),
        ),
    )


check_plugin_palo_alto_users = CheckPlugin(
    name="palo_alto_users",
    service_name="Palo Alto Users",
    discovery_function=discover,
    check_function=check,
    cluster_check_function=cluster_check,
    check_ruleset_name="palo_alto_users_rule",
    check_default_parameters={"levels": "ignore"},
)
