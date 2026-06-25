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
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState
from cmk.plugins.ups.lib_socomec import DETECT_SOCOMEC

Section = Mapping[str, ElPhase]


def parse_ups_socomec_outphase(string_table: StringTable) -> Section:
    parsed: dict[str, ElPhase] = {}
    for index, rawvolt, rawcurr, rawload in string_table:
        parsed["Phase " + index] = ElPhase(
            # The actual precision does not appear to go beyond degrees, thus we drop the trailing 0
            voltage=ReadingWithState(value=int(rawvolt) // 10),
            current=ReadingWithState(value=int(rawcurr) // 10),
            output_load=ReadingWithState(value=int(rawload)),
        )
    return parsed


def discover_ups_socomec_outphase(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_ups_socomec_outphase(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not item.startswith("Phase"):
        # fix item names discovered before 1.2.7
        item = "Phase %s" % item
    if phase := section.get(item):
        yield from check_elphase(params, phase)


snmp_section_ups_socomec_outphase = SimpleSNMPSection(
    name="ups_socomec_outphase",
    detect=DETECT_SOCOMEC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.4.4.1",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_ups_socomec_outphase,
)


check_plugin_ups_socomec_outphase = CheckPlugin(
    name="ups_socomec_outphase",
    service_name="Output %s",
    discovery_function=discover_ups_socomec_outphase,
    check_function=check_ups_socomec_outphase,
    check_ruleset_name="ups_outphase",
    # Phase Index, Voltage/dV, Current/dA, Load/%,
    check_default_parameters={
        "voltage": (210, 200),
        "output_load": (80, 90),
    },
)
