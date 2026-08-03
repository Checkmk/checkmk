#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState

Section = Mapping[str, ElPhase]


def parse_bluenet_meter(string_table: StringTable) -> Section:
    parsed: dict[str, ElPhase] = {}
    for meter_id, power_p, power_s, u_rms, i_rms in string_table:
        # do not take into account powermeters with no voltage
        if u_rms != "0":
            parsed[meter_id] = ElPhase(
                voltage=ReadingWithState(value=float(u_rms) / 1000.0),
                current=ReadingWithState(value=float(i_rms) / 1000.0),
                power=ReadingWithState(value=float(power_p)),
                appower=ReadingWithState(value=float(power_s)),
            )
    return parsed


snmp_section_bluenet_meter = SimpleSNMPSection(
    name="bluenet_meter",
    parse_function=parse_bluenet_meter,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21695.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21695.1.10.7.2.1",
        oids=["1", "5", "7", "8", "9"],
    ),
)


def discover_bluenet_meter(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_bluenet_meter(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (elphase := section.get(item)) is None:
        return
    yield from check_elphase(params, elphase)


check_plugin_bluenet_meter = CheckPlugin(
    name="bluenet_meter",
    service_name="Powermeter %s",
    discovery_function=discover_bluenet_meter,
    check_function=check_bluenet_meter,
    check_ruleset_name="ups_outphase",
    check_default_parameters={},
)
