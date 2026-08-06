#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.domino.lib import DETECT
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel


class DominoUsersParams(TypedDict):
    levels: SimpleLevelsConfigModel[int]


def discover_domino_users(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_domino_users(params: DominoUsersParams, section: StringTable) -> CheckResult:
    try:
        users = int(section[0][0])
    except IndexError:
        return

    yield from check_levels(
        users,
        levels_upper=params["levels"],
        metric_name="users",
        render_func=str,
        label="Domino users on server",
    )


def parse_domino_users(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_domino_users = SimpleSNMPSection(
    name="domino_users",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.334.72.1.1.6.3",
        oids=["6"],
    ),
    parse_function=parse_domino_users,
)


check_plugin_domino_users = CheckPlugin(
    name="domino_users",
    service_name="Domino Users",
    discovery_function=discover_domino_users,
    check_function=check_domino_users,
    check_ruleset_name="domino_users",
    check_default_parameters=DominoUsersParams(levels=("fixed", (1000, 1500))),
)
