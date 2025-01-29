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
from cmk.plugins.cisco_sma.agent_based.detect import DETECT_CISCO_SMA_SNMP
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel


class Params(TypedDict):
    levels_upper: SimpleLevelsConfigModel[float]
    levels_lower: SimpleLevelsConfigModel[float]


def _check_files_and_sockets(params: Params, section: float) -> CheckResult:
    yield from check_levels(
        section,
        label="Open",
        metric_name="cisco_sma_files_and_sockets",
        render_func=lambda x: str(int(x)),
        levels_upper=params["levels_upper"],
        levels_lower=params["levels_lower"],
    )


def _discover_files_and_sockets(section: float) -> DiscoveryResult:
    yield Service()


check_plugin_files_and_sockets = CheckPlugin(
    name="cisco_sma_files_and_sockets",
    service_name="Files and sockets",
    discovery_function=_discover_files_and_sockets,
    check_function=_check_files_and_sockets,
    check_ruleset_name="generic_numeric_value_without_item",
    check_default_parameters=Params(
        levels_upper=("fixed", (5500.0, 6000.0)),
        levels_lower=("fixed", (0.0, 0.0)),
    ),
)


def _parse_files_or_sockets(string_table: StringTable) -> float | None:
    if not string_table or not string_table[0]:
        return None

    return float(string_table[0][0])


snmp_section_files_and_sockets = SimpleSNMPSection(
    parsed_section_name="cisco_sma_files_and_sockets",
    name="cisco_sma_files_and_sockets",
    detect=DETECT_CISCO_SMA_SNMP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["19"],
    ),
    parse_function=_parse_files_or_sockets,
)
