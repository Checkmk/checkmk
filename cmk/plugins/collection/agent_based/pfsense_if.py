#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_rate,
    get_value_store,
    LevelsT,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)


@dataclass(frozen=True)
class Packets:
    ip4_in_blocked: int


Section = Mapping[str, Packets]


class Params(TypedDict):
    ipv4_in_blocked: LevelsT[float]


def parse_pfsense_if(string_table: StringTable) -> Section:
    return {name: Packets(ip4_in_blocked=int(value)) for name, value in string_table}


def inventory_pfsense_if(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_firewall_if(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_firewall_if_testable(item, params, section, get_value_store(), time.time())


def check_firewall_if_testable(
    item: str,
    params: Params,
    section: Section,
    value_store: MutableMapping[str, object],
    this_time: float,
) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    yield from check_levels(
        get_rate(
            value_store,
            "ip4_in_blocked",
            this_time,
            data.ip4_in_blocked,
            raise_overflow=True,
        ),
        metric_name="ip4_in_blocked",
        levels_upper=params["ipv4_in_blocked"],
        render_func=lambda x: f"{x:.2f} pkts/s",
        label="Incoming IPv4 packets blocked",
    )


snmp_section_pfsense_if = SimpleSNMPSection(
    name="pfsense_if",
    detect=contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12325.1.200.1.8.2.1",
        oids=["2", "12"],
    ),
    parse_function=parse_pfsense_if,
)


DEFAULT_PARAMETERS = Params(
    ipv4_in_blocked=("fixed", (100.0, 10000.0)),
)


check_plugin_pfsense_if = CheckPlugin(
    name="pfsense_if",
    service_name="Firewall Interface %s",
    discovery_function=inventory_pfsense_if,
    check_function=check_firewall_if,
    check_ruleset_name="firewall_if",
    check_default_parameters=DEFAULT_PARAMETERS,
)
