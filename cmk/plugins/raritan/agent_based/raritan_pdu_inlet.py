#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingState, ReadingWithState
from cmk.plugins.raritan.lib import (
    DETECT_RARITAN,
    elphase_from_readings,
    STATE_MAPPING,
    TYPE_MAPPING,
)

type Section = Mapping[str, ElPhase]


def parse_raritan_pdu_inlet(string_table: Sequence[StringTable]) -> Section:
    precisions = {oid_end: int(decimals) for oid_end, decimals in string_table[0]}
    readings: dict[str, dict[str, ReadingWithState]] = {}
    for oid_end, availability, sensor_state, value_str in string_table[1]:
        if availability != "1":
            continue
        phase_id, sensor_type = oid_end.split(".")[2:4]
        if sensor_type not in TYPE_MAPPING:
            continue
        key, _key_info = TYPE_MAPPING[sensor_type]
        value = float(value_str) / 10 ** precisions[oid_end]
        state, state_readable = STATE_MAPPING[sensor_state]
        readings.setdefault(f"Phase {phase_id}", {})[key] = ReadingWithState(
            value=value,
            state=None if state is State.OK else ReadingState(state=state, text=state_readable),
        )
    return {
        phase: elphase_from_readings(phase_readings) for phase, phase_readings in readings.items()
    }


def check_raritan_pdu_inlet(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not item.startswith("Phase"):
        item = f"Phase {item}"
    if (elphase := section.get(item)) is None:
        return
    yield from check_elphase(params, elphase)


def discover_raritan_pdu_inlet(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_raritan_pdu_inlet = SNMPSection(
    name="raritan_pdu_inlet",
    detect=DETECT_RARITAN,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.3.6.1",
            oids=[OIDEnd(), "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.5.2.4.1",
            oids=[OIDEnd(), "2", "3", "4"],
        ),
    ],
    parse_function=parse_raritan_pdu_inlet,
)


check_plugin_raritan_pdu_inlet = CheckPlugin(
    name="raritan_pdu_inlet",
    service_name="Input %s",
    discovery_function=discover_raritan_pdu_inlet,
    check_function=check_raritan_pdu_inlet,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
