#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# example output

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

Section = Mapping


def parse_cisco_asa_conn(string_table: Sequence[StringTable]) -> Section:
    parsed = {}
    for line in string_table[0]:
        parsed[line[0]] = [line[1]]
    for line in string_table[2]:
        parsed[line[0]].append(line[1])
        parsed[line[0]].append(line[2])
    for line in string_table[1]:
        parsed[line[0]].append(line[1])

    return parsed


def inventory_cisco_asa_conn(section: Section) -> DiscoveryResult:
    for key, values in section.items():
        if values[1] == "1" and len(values) == 4:
            yield Service(item=key)


def check_cisco_asa_conn(item: str, section: Section) -> CheckResult:
    translate_status = {
        "1": (State.OK, "up"),
        "2": (State.CRIT, "down"),
        "3": (State.UNKNOWN, "testing"),
        "4": (State.UNKNOWN, "unknown"),
        "5": (State.CRIT, "dormant"),
        "6": (State.CRIT, "not present"),
        "7": (State.CRIT, "lower layer down"),
    }

    for key, values in section.items():
        if item == key:
            yield Result(state=State.OK, summary="Name: %s" % values[0])

            try:
                ip_address = values[3]
            except IndexError:
                ip_address = None

            if ip_address:
                yield Result(state=State.OK, summary="IP: %s" % ip_address)
            else:  # CRIT if no IP is assigned
                yield Result(state=State.CRIT, summary="IP: Not found!")

            state, state_readable = translate_status.get(values[2], (State.UNKNOWN, "N/A"))
            yield Result(state=state, summary="Status: %s" % state_readable)


snmp_section_cisco_asa_conn = SNMPSection(
    name="cisco_asa_conn",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.1.0", "cisco adaptive security"),
        startswith(".1.3.6.1.2.1.1.1.0", "cisco firewall services"),
        contains(".1.3.6.1.2.1.1.1.0", "cisco pix security"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.31.1.1.1",
            oids=[OIDEnd(), "1"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.4.20.1",
            oids=["2", "1"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[OIDEnd(), "7", "8"],
        ),
    ],
    parse_function=parse_cisco_asa_conn,
)


check_plugin_cisco_asa_conn = CheckPlugin(
    name="cisco_asa_conn",
    service_name="Connection %s",
    discovery_function=inventory_cisco_asa_conn,
    check_function=check_cisco_asa_conn,
)
