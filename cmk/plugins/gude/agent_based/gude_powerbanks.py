#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState

# Knowledge from customer:
# Devices with OID_END=38 are 12 port power switches with two powerbanks.
# Means each powerbank has 6 outlets. Here we can use ChanStatus in order
# to find out if one powerbank is enabled/used.
#
# Device with OID_END=19 is a simple switch outlet: 1 Port and 1 powerbank
# Once it's plugged in, the state is "on". Thus we use PortState in
# discovering function.

_TABLES = (19, 38)

_PORT_STATES = {
    "0": (State.CRIT, "off"),
    "1": (State.OK, "on"),
}
_CHANNEL_STATES = {
    "0": (State.CRIT, "data not active"),
    "1": (State.OK, "data valid"),
}

Section = Mapping[str, ElPhase]


def parse_gude_powerbanks(string_table: Sequence[StringTable]) -> Section:
    ports = dict(string_table[0])

    parsed: dict[str, ElPhase] = {}
    for oid, block in zip(_TABLES, string_table[2:]):
        for idx, dev_state, energy, active_power, current, volt, freq, appower in block:
            device_state = _PORT_STATES[ports[idx]] if oid == 19 else _CHANNEL_STATES[dev_state]
            parsed[idx] = ElPhase(
                device_state=device_state,
                energy=ReadingWithState(value=float(energy)),
                power=ReadingWithState(value=float(active_power)),
                current=ReadingWithState(value=float(current) * 0.001),
                voltage=ReadingWithState(value=float(volt)),
                frequency=ReadingWithState(value=float(freq) * 0.01),
                appower=ReadingWithState(value=float(appower)),
            )

    return parsed


def discover_gude_powerbanks(section: Section) -> DiscoveryResult:
    for powerbank, elphase in section.items():
        assert elphase.device_state is not None
        if elphase.device_state[1] not in ("off", "data not active"):
            yield Service(item=powerbank)


def check_gude_powerbanks(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (elphase := section.get(item)) is None:
        return
    yield from check_elphase(params, elphase)


snmp_section_gude_powerbanks = SNMPSection(
    name="gude_powerbanks",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.19"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.38"),
    ),
    fetch=[
        SNMPTree(
            base=f".1.3.6.1.4.1.28507.{table}.1.3.1.2.1",
            oids=[OIDEnd(), "3"],
        )
        for table in _TABLES
    ]
    + [
        SNMPTree(
            base=f".1.3.6.1.4.1.28507.{table}.1.5.1.2.1",
            oids=[OIDEnd(), "2", "3", "4", "5", "6", "7", "10"],
        )
        for table in _TABLES
    ],
    parse_function=parse_gude_powerbanks,
)


check_plugin_gude_powerbanks = CheckPlugin(
    name="gude_powerbanks",
    service_name="Powerbank %s",
    discovery_function=discover_gude_powerbanks,
    check_function=check_gude_powerbanks,
    check_ruleset_name="el_inphase",
    check_default_parameters={
        "voltage": (220, 210),
        "current": (15, 16),
    },
)
