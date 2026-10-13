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
    OIDEnd,
    Service,
    SimpleSNMPSection,
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


def parse_raritan_pdu_inlet_summary(string_table: StringTable) -> Section | None:
    readings: dict[str, ReadingWithState] = {}
    for sensor_type, decimal_digits, availability, sensor_state, value_str in string_table:
        if availability == "1" and sensor_type in TYPE_MAPPING:  # handled sensor types
            key, _key_info = TYPE_MAPPING[sensor_type]
            value = float(value_str) / 10 ** int(decimal_digits)
            state, state_readable = STATE_MAPPING[sensor_state]
            readings[key] = ReadingWithState(
                value=value,
                state=None if state is State.OK else ReadingState(state=state, text=state_readable),
            )

    return {"Summary": elphase_from_readings(readings)} if readings else None


def discover_raritan_pdu_inlet_summary(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_raritan_pdu_inlet_summary(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (elphase := section.get(item)) is None:
        return
    yield from check_elphase(params, elphase)


snmp_section_raritan_pdu_inlet_summary = SimpleSNMPSection(
    name="raritan_pdu_inlet_summary",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6",
        oids=[OIDEnd(), "3.3.4.1.7.1.1", "5.2.3.1.2.1.1", "5.2.3.1.3.1.1", "5.2.3.1.4.1.1"],
    ),
    parse_function=parse_raritan_pdu_inlet_summary,
)


check_plugin_raritan_pdu_inlet_summary = CheckPlugin(
    name="raritan_pdu_inlet_summary",
    service_name="Input %s",
    discovery_function=discover_raritan_pdu_inlet_summary,
    check_function=check_raritan_pdu_inlet_summary,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
