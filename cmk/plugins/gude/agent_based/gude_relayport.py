#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import asdict, dataclass

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
from cmk.plugins.lib.elphase import check_elphase, CheckParams

# .1.3.6.1.4.1.28507.38.1.3.1.2.1.2.1 TWTA 2 --> GUDEADS-EPC822X-MIB::epc822XPortName.1
# .1.3.6.1.4.1.28507.38.1.3.1.2.1.3.1 0 --> GUDEADS-EPC822X-MIB::epc822XPortState.1
# .1.3.6.1.4.1.28507.38.1.5.1.2.1.4.1 0 --> GUDEADS-EPC822X-MIB::epc822XspPowerActive.1
# .1.3.6.1.4.1.28507.38.1.5.1.2.1.5.1 0 --> GUDEADS-EPC822X-MIB::epc822XspCurrent.1
# .1.3.6.1.4.1.28507.38.1.5.1.2.1.6.1 228 --> GUDEADS-EPC822X-MIB::epc822XspVoltage.1
# .1.3.6.1.4.1.28507.38.1.5.1.2.1.7.1 4995 --> GUDEADS-EPC822X-MIB::epc822XspFrequency.1
# .1.3.6.1.4.1.28507.38.1.5.1.2.1.10.1 0 --> GUDEADS-EPC822X-MIB::epc822XspPowerApparent.1

_STATE_MAP = {
    "0": (2, "off"),
    "1": (0, "on"),
}


@dataclass(frozen=True, kw_only=True)
class RelayPort:
    device_state: tuple[int, str]
    power: float | None
    current: float | None
    voltage: float | None
    frequency: float | None
    appower: float | None


Section = Mapping[str, RelayPort]


def parse_gude_relayport(string_table: StringTable) -> Section:
    return {
        portname: RelayPort(
            device_state=_STATE_MAP[state],
            power=float(power) if power else None,
            current=float(current) * 0.001 if current else None,
            voltage=float(voltage) if voltage else None,
            frequency=float(freq) * 0.01 if freq else None,
            appower=float(appower) if appower else None,
        )
        for portname, state, power, current, voltage, freq, appower in string_table
    }


snmp_section_gude_relayport = SimpleSNMPSection(
    name="gude_relayport",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.28507.38"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.28507.38.1",
        oids=[
            "3.1.2.1.2",  # GUDEADS-EPC822X-MIB::epc822XPortName.1
            "3.1.2.1.3",  # GUDEADS-EPC822X-MIB::epc822XPortState.1
            "5.5.2.1.4",  # GUDEADS-EPC822X-MIB::epc822XspPowerActive.1
            "5.5.2.1.5",  # GUDEADS-EPC822X-MIB::epc822XspCurrent.1
            "5.5.2.1.6",  # GUDEADS-EPC822X-MIB::epc822XspVoltage.1
            "5.5.2.1.7",  # GUDEADS-EPC822X-MIB::epc822XspFrequency.1
            "5.5.2.1.10",  # GUDEADS-EPC822X-MIB::epc822XspPowerApparent.1
        ],
    ),
    parse_function=parse_gude_relayport,
)


def discover_gude_relayport(
    section: Section,
) -> DiscoveryResult:
    yield from (Service(item=relayport) for relayport in section)


def check_gude_relayport(item: str, params: CheckParams, section: Section) -> CheckResult:
    if (relayport := section.get(item)) is None:
        return

    yield from check_elphase(
        item, params, {item: {k: v for k, v in asdict(relayport).items() if v is not None}}
    )


check_plugin_gude_relayport = CheckPlugin(
    name="gude_relayport",
    service_name="Relay port %s",
    discovery_function=discover_gude_relayport,
    check_function=check_gude_relayport,
    check_ruleset_name="el_inphase",
    check_default_parameters={
        "voltage": (220, 210),
        "current": (15, 16),
    },
)
