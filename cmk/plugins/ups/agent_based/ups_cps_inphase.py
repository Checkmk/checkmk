#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.plugins.lib.elphase import check_elphase, ElPhase
from cmk.plugins.ups.lib import DETECT_UPS_CPS

Section = Mapping[str, ElPhase]


def parse_ups_cps_inphase(string_table: StringTable) -> Section | None:
    if not string_table:
        return None

    parsed: dict[str, float] = {}
    for index, stat_name in enumerate(("voltage", "frequency")):
        try:
            parsed[stat_name] = float(string_table[0][index]) / 10
        except ValueError:
            continue

    return {"1": ElPhase.from_dict(parsed)} if parsed else {}


def discover_ups_cps_inphase(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_ups_cps_inphase(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if phase := section.get(item):
        yield from check_elphase(params, phase)


snmp_section_ups_cps_inphase = SimpleSNMPSection(
    name="ups_cps_inphase",
    detect=DETECT_UPS_CPS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3808.1.1.1.3.2",
        oids=["1", "4"],
    ),
    parse_function=parse_ups_cps_inphase,
)


check_plugin_ups_cps_inphase = CheckPlugin(
    name="ups_cps_inphase",
    service_name="UPS Input Phase %s",
    discovery_function=discover_ups_cps_inphase,
    check_function=check_ups_cps_inphase,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
