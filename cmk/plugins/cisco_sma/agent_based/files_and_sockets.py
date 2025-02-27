#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel

from .detect import DETECT_CISCO_SMA


class Params(TypedDict):
    levels_upper_open_files_and_sockets: SimpleLevelsConfigModel[int]
    levels_lower_open_files_and_sockets: SimpleLevelsConfigModel[int]


def _check_files_and_sockets(params: Params, section: int) -> CheckResult:
    yield from check_levels(
        section,
        label="Open",
        metric_name="cisco_sma_files_and_sockets",
        render_func=lambda x: str(int(x)),
        levels_upper=params["levels_upper_open_files_and_sockets"],
        levels_lower=params["levels_lower_open_files_and_sockets"],
    )


def _discover_files_and_sockets(section: int) -> DiscoveryResult:
    yield Service()


check_plugin_files_and_sockets = CheckPlugin(
    name="cisco_sma_files_and_sockets",
    service_name="Files and sockets",
    discovery_function=_discover_files_and_sockets,
    check_function=_check_files_and_sockets,
    check_ruleset_name="cisco_sma_files_and_sockets",
    check_default_parameters=Params(
        levels_upper_open_files_and_sockets=("fixed", (5500, 6000)),
        levels_lower_open_files_and_sockets=("no_levels", None),
    ),
)


def _parse_files_and_sockets(string_table: StringTable) -> int | None:
    if not string_table or not string_table[0]:
        return None

    return int(string_table[0][0])


snmp_section_files_and_sockets = SimpleSNMPSection(
    parsed_section_name="cisco_sma_files_and_sockets",
    name="cisco_sma_files_and_sockets",
    detect=DETECT_CISCO_SMA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["19"],
    ),
    parse_function=_parse_files_and_sockets,
)
