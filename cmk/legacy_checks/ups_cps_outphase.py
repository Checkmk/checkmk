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
from cmk.plugins.lib.elphase import check_elphase, ElPhase
from cmk.plugins.ups.lib import DETECT_UPS_CPS

Section = Mapping[str, ElPhase]


def parse_ups_cps_outphase(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    line = string_table[0]
    return {
        "1": ElPhase.from_dict(
            {
                "voltage": float(line[0]) / 10,
                "frequency": float(line[1]) / 10,
                "output_load": float(line[2]),
                "current": float(line[3]) / 10,
            }
        )
    }


def discover_ups_cps_outphase(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_ups_cps_outphase(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if phase := section.get(item):
        yield from check_elphase(params, phase)


snmp_section_ups_cps_outphase = SimpleSNMPSection(
    name="ups_cps_outphase",
    detect=DETECT_UPS_CPS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3808.1.1.1.4.2",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_ups_cps_outphase,
)


check_plugin_ups_cps_outphase = CheckPlugin(
    name="ups_cps_outphase",
    service_name="UPS Output Phase %s",
    discovery_function=discover_ups_cps_outphase,
    check_function=check_ups_cps_outphase,
    check_ruleset_name="ups_outphase",
    check_default_parameters={},
)
