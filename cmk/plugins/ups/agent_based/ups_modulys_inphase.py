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
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState
from cmk.plugins.lib.ups_modulys import DETECT_UPS_MODULYS


def parse_ups_modulys_inphase(string_table: StringTable) -> dict[str, ElPhase] | None:
    if not string_table:
        return None

    first_line = string_table[0]
    parsed = {}
    if phase_1 := _parse_phase(first_line[1], first_line[2], first_line[3]):
        parsed["Phase 1"] = phase_1

    if first_line[0] == "3":
        if phase_2 := _parse_phase(first_line[4], first_line[5], first_line[6]):
            parsed["Phase 2"] = phase_2
        if phase_3 := _parse_phase(first_line[7], first_line[8], first_line[9]):
            parsed["Phase 3"] = phase_3

    return parsed


def _parse_phase(raw_frequency: str, raw_voltage: str, raw_current: str) -> ElPhase | None:
    return ElPhase(
        frequency=_parse_value(raw_frequency),
        voltage=_parse_value(raw_voltage),
        current=_parse_value(raw_current),
    )


def _parse_value(raw_value: str) -> ReadingWithState | None:
    return ReadingWithState(value=int(raw_value) / 10.0) if raw_value.isdigit() else None


snmp_section_ups_modulys_inphase = SimpleSNMPSection(
    name="ups_modulys_inphase",
    detect=DETECT_UPS_MODULYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2254.2.4.4",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    ),
    parse_function=parse_ups_modulys_inphase,
)


def discover_ups_modulys_inphase(section: Mapping[str, Mapping[str, float]]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_ups_modulys_inphase(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, ElPhase],
) -> CheckResult:
    if inphase := section.get(item):
        yield from check_elphase(params, inphase)


check_plugin_ups_test = CheckPlugin(
    name="ups_modulys_inphase",
    service_name="Input %s",
    discovery_function=discover_ups_modulys_inphase,
    check_function=check_ups_modulys_inphase,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
