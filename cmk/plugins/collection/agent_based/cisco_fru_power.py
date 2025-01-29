#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.22 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.23 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.470 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.471 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.472 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.473 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.113000022 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.113000470 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.113000471 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.116000022 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.116000470 2
# .1.3.6.1.4.1.9.9.117.1.1.2.1.2.116000471 2

# .1.3.6.1.2.1.47.1.1.1.1.7.10 Fabric [VPC domain:12]
# .1.3.6.1.2.1.47.1.1.1.1.7.22 Nexus 56128P Supervisor in Fixed Module-1
# .1.3.6.1.2.1.47.1.1.1.1.7.23 24 ports 10GE SFP+ and 2xQSFP ports Ethernet Module
# .1.3.6.1.2.1.47.1.1.1.1.7.149 Nexus 56128P Chassis
# .1.3.6.1.2.1.47.1.1.1.1.7.214 Fixed Slot-1
# .1.3.6.1.2.1.47.1.1.1.1.7.215 Module Slot-2
# .1.3.6.1.2.1.47.1.1.1.1.7.216 Module Slot-3
# .1.3.6.1.2.1.47.1.1.1.1.7.278 PowerSupplyBay-1
# .1.3.6.1.2.1.47.1.1.1.1.7.279 PowerSupplyBay-2
# .1.3.6.1.2.1.47.1.1.1.1.7.280 PowerSupplyBay-3
# .1.3.6.1.2.1.47.1.1.1.1.7.281 PowerSupplyBay-4
# .1.3.6.1.2.1.47.1.1.1.1.7.342 FanBay-1
# .1.3.6.1.2.1.47.1.1.1.1.7.343 FanBay-2
# .1.3.6.1.2.1.47.1.1.1.1.7.344 FanBay-3
# .1.3.6.1.2.1.47.1.1.1.1.7.345 FanBay-4
# .1.3.6.1.2.1.47.1.1.1.1.7.470 PowerSupply-1
# .1.3.6.1.2.1.47.1.1.1.1.7.471 PowerSupply-2
# .1.3.6.1.2.1.47.1.1.1.1.7.472 PowerSupply-3
# .1.3.6.1.2.1.47.1.1.1.1.7.473 PowerSupply-4
# .1.3.6.1.2.1.47.1.1.1.1.7.534 FanModule-1
# .1.3.6.1.2.1.47.1.1.1.1.7.535 FanModule-2
# .1.3.6.1.2.1.47.1.1.1.1.7.536 FanModule-3
# .1.3.6.1.2.1.47.1.1.1.1.7.537 FanModule-4
# .1.3.6.1.2.1.47.1.1.1.1.7.538 PowerSupply-1 Fan-1
# .1.3.6.1.2.1.47.1.1.1.1.7.539 PowerSupply-1 Fan-2
# .1.3.6.1.2.1.47.1.1.1.1.7.540 PowerSupply-2 Fan-1
# .1.3.6.1.2.1.47.1.1.1.1.7.541 PowerSupply-2 Fan-2
# ...


from collections.abc import Container, Mapping, Sequence
from dataclasses import dataclass
from itertools import groupby
from typing import Final

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    not_exists,
    OIDCached,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)


@dataclass(frozen=True)
class FRU:
    state: int
    current: int


Section = Mapping[str, FRU]

_STATE_MAP: Final = {
    1: (State.WARN, "off env other"),
    2: (State.OK, "on"),
    3: (State.WARN, "off admin"),
    4: (State.CRIT, "off denied"),
    5: (State.CRIT, "off env power"),
    6: (State.CRIT, "off env temp"),
    7: (State.CRIT, "off env fan"),
    8: (State.CRIT, "failed"),
    9: (State.WARN, "on but fan fail"),
    10: (State.WARN, "off cooling"),
    11: (State.WARN, "off connector rating"),
    12: (State.CRIT, "on but inline power fail"),
}


def parse_cisco_fru_power(string_table: Sequence[StringTable]) -> Section:
    states_and_currents, names = string_table

    raw_states = {oid_end: oper_state for oid_end, oper_state, _current in states_and_currents}
    raw_currents = {oid_end: current for oid_end, _oper_state, current in states_and_currents}

    name_map = _oid_name_map(names, raw_states)

    return {
        name: fru
        for name, oid_end in name_map.items()
        if (fru := _make_fru(raw_states[oid_end], raw_currents[oid_end])) and _is_real_psu(fru)
    }


def _make_fru(raw_state: str, raw_current: str) -> FRU | None:
    try:
        return FRU(state=int(raw_state), current=int(raw_current))
    except ValueError:
        return None


def _is_real_psu(fru: FRU) -> bool:
    # We discover only "real" power supplies which have current value >= 0
    # Others such as modules do not have such values
    return fru.state != 0 and fru.current >= 0


def _oid_name_map(names: StringTable, filter_oids: Container[str]) -> Mapping[str, str]:
    return {
        name if len(oid_ends) == 1 else f"{name}-{num}": oid_end
        for name, oid_ends_names in groupby(sorted(names, key=lambda x: x[1]), key=lambda x: x[1])
        if (oid_ends := [oe for oe, _name in oid_ends_names if oe in filter_oids])
        for num, oid_end in enumerate(oid_ends, start=1)
    }


def discover_cisco_fru_power(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, fru in section.items() if fru.state not in (1, 3))


def check_cisco_fru_power(item: str, section: Section) -> CheckResult:
    if (fru := section.get(item)) is None:
        return

    state, state_readable = _STATE_MAP.get(fru.state, (State.UNKNOWN, f"unexpected ({fru.state})"))
    yield Result(state=state, summary="Status: %s" % state_readable)


snmp_section_cisco_fru_power = SNMPSection(
    name="cisco_fru_power",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), not_exists(".1.3.6.1.4.1.9.9.13.1.5.1.*")
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.117.1.1.2.1",
            oids=[OIDEnd(), "2", "3"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), OIDCached("7")],
        ),
    ],
    parse_function=parse_cisco_fru_power,
)

check_plugin_cisco_fru_power = CheckPlugin(
    name="cisco_fru_power",
    service_name="FRU Power %s",
    discovery_function=discover_cisco_fru_power,
    check_function=check_cisco_fru_power,
)
