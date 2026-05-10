#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.apc.lib_ats import DETECT
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState

# .1.3.6.1.4.1.318.1.1.1.3.2.1.0 231

type Section = Mapping[str, ElPhase]


def parse_apc_symmetra_input(string_table: StringTable) -> Section:
    if not string_table:
        return {}
    return {
        "Input": ElPhase(
            voltage=ReadingWithState(value=float(string_table[0][0])),
        )
    }


def discover_apc_symmetra_input(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_apc_symmetra_input(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    yield from check_elphase(params, data)


snmp_section_apc_symmetra_input = SimpleSNMPSection(
    name="apc_symmetra_input",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.1.3.2",
        oids=["1"],
    ),
    parse_function=parse_apc_symmetra_input,
)


check_plugin_apc_symmetra_input = CheckPlugin(
    name="apc_symmetra_input",
    service_name="Phase %s",
    discovery_function=discover_apc_symmetra_input,
    check_function=check_apc_symmetra_input,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
