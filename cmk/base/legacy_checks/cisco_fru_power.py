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


# mypy: disable-error-code="var-annotated"

from collections.abc import Container, Iterable, Mapping
from itertools import groupby
from typing import Final, List

from cmk.base.check_api import all_of, contains, LegacyCheckDefinition, not_exists
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDCached, OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

DiscoveryResult = Iterable[tuple[str, dict]]
CheckResult = Iterable[tuple[int, str]]

Section = Mapping[str, tuple[int, str]]

_STATE_MAP: Final = {
    "1": (1, "off env other"),
    "2": (0, "on"),
    "3": (1, "off admin"),
    "4": (2, "off denied"),
    "5": (2, "off env power"),
    "6": (2, "off env temp"),
    "7": (2, "off env fan"),
    "8": (2, "failed"),
    "9": (1, "on but fan fail"),
    "10": (1, "off cooling"),
    "11": (1, "off connector rating"),
    "12": (2, "on but inline power fail"),
}


def parse_cisco_fru_power(string_table: List[StringTable]) -> Section:
    states_and_currents, names = string_table

    raw_states = {oid_end: oper_state for oid_end, oper_state, _current in states_and_currents}
    raw_currents = {oid_end: current for oid_end, _oper_state, current in states_and_currents}

    name_map = _oid_name_map(names, raw_states)

    return {
        name: _STATE_MAP.get(raw_states[oid_end], (3, "unexpected(%s)" % raw_states[oid_end]))
        for name, oid_end in name_map.items()
        if _is_real_psu(raw_states[oid_end], raw_currents[oid_end])
    }


def _is_real_psu(oper_state: str, current: str) -> bool:
    # We discover only "real" power supplies which have current value >= 0
    # Others such as modules do not have such values
    return oper_state not in ["", "0", "1", "5"] and bool(current) and int(current) >= 0


def _oid_name_map(names: StringTable, filter_oids: Container[str]) -> Mapping[str, str]:
    return {
        name if len(oid_ends) == 1 else f"{name}-{num}": oid_end
        for name, oid_ends_names in groupby(sorted(names, key=lambda x: x[1]), key=lambda x: x[1])
        if (oid_ends := [oe for oe, _name in oid_ends_names if oe in filter_oids])
        for num, oid_end in enumerate(oid_ends, start=1)
    }


def discover_cisco_fru_power(section: Section) -> DiscoveryResult:
    yield from ((item, {}) for item in section)


def check_cisco_fru_power(item: str, _no_params: object, section: Section) -> CheckResult:
    if (fru := section.get(item)) is None:
        return

    state, state_readable = fru
    yield state, "Status: %s" % state_readable


check_info["cisco_fru_power"] = LegacyCheckDefinition(
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), not_exists(".1.3.6.1.4.1.9.9.13.1.5.1.*")
    ),
    parse_function=parse_cisco_fru_power,
    discovery_function=discover_cisco_fru_power,
    check_function=check_cisco_fru_power,
    service_name="FRU Power %s",
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
)
