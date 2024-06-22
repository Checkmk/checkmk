#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def parse_zebra_printer_status(string_table: StringTable) -> str | None:
    return string_table[0][0] if string_table else None


def inventory_zebra_printer_status(section: str) -> DiscoveryResult:
    if section:
        yield Service()


def check_zebra_printer_status(section: str) -> CheckResult:
    zebra_status = section

    if zebra_status == "3":
        yield Result(state=State.OK, summary="Printer is online and ready for the next print job")
        return
    if zebra_status == "4":
        yield Result(state=State.OK, summary="Printer is printing")
        return
    if zebra_status == "5":
        yield Result(state=State.OK, summary="Printer is warming up")
        return
    if zebra_status == "1":
        yield Result(state=State.CRIT, summary="Printer is offline")
        return
    yield Result(state=State.UNKNOWN, summary="Unknown printer status")
    return


snmp_section_zebra_printer_status = SimpleSNMPSection(
    name="zebra_printer_status",
    detect=contains(".1.3.6.1.2.1.1.1.0", "zebra"),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.25.3.5.1.1",
        oids=["1"],
    ),
    parse_function=parse_zebra_printer_status,
)
check_plugin_zebra_printer_status = CheckPlugin(
    name="zebra_printer_status",
    service_name="Zebra Printer Status",
    discovery_function=inventory_zebra_printer_status,
    check_function=check_zebra_printer_status,
)
