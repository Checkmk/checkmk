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
    contains,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

Section = dict[str, dict[str, str]]


def parse_seh_ports(string_table: Sequence[StringTable]) -> Section:
    parsed: Section = {}
    for oid_end, tag, status, port_number in string_table[0] or string_table[1]:
        oid_index = oid_end.split(".")[0]
        if tag != "":
            parsed.setdefault(oid_index, {}).update(tag=tag)
        if port_number != "0":
            parsed.setdefault(port_number, {}).update(status=status)
    return parsed


snmp_section_seh_ports = SNMPSection(
    name="seh_ports",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1229.1.1"),
    fetch=[
        # format taken from SEH-PSRV-MIB v1.167 (2021.10.15)
        SNMPTree(
            # SEH-PSRV-MIB::sehPSrv(2).sehUtn(50).utnPortTable(2).utnPortEntry(1)
            base=".1.3.6.1.4.1.1229.2.50.2.1",
            oids=[
                OIDEnd(),  # index
                "10",  # utnPortTag: UTN USB port short description string
                "26",  # utnPortUsbOwn: UTN USB device connection status
                "27",  # utnPortSlot: UTN slot number the USB is attached to
            ],
        ),
        # format taken from SEH-MIB v2.5 (2023.10.31)
        SNMPTree(
            # In MIB v2.5 `utnPortTag` and the other details are located in
            # different subtrees:
            # SEH-MIB::seh(1229).sehUtn(5)
            #   .sehUtnPortTab(10)
            #       .utnPortNumber(1)
            #       .utnPortTable(2).utnPortEntry(1)
            #           .utnPortTag(10): UTN USB port short description string
            #   .sehUtnDevTab(20)
            #       .utnDevNumber(1)
            #       .utnDevTable(2).utnDevEntry(1)
            #           .utnDevOwn(7): UTN USB device connection status
            #           .utnDevPort(7): UTN slot number the USB is attached to
            base=".1.3.6.1.4.1.1229.5",
            oids=[
                OIDEnd(),  # index
                "10.2.1.10",  # utnPortTag: UTN USB port short description string
                "20.2.1.7",  # utnDevOwn: UTN USB device connection status
                "20.2.1.8",  # utnDevPort: UTN slot number the USB is attached to
            ],
        ),
    ],
    parse_function=parse_seh_ports,
)


def discover_seh_ports(section: Section) -> DiscoveryResult:
    for key, port in section.items():
        yield Service(item=key, parameters={"status_at_discovery": port.get("status")})


def check_seh_ports(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    for key in ("tag", "status"):
        if key in data:
            yield Result(state=State.OK, summary=f"{key.title()}: {data[key]}")

    if params.get("status_at_discovery") != data.get("status"):
        yield Result(
            state=State.WARN,
            summary=f"Status during discovery: {params.get('status_at_discovery') or 'unknown'}",
        )


check_plugin_seh_ports = CheckPlugin(
    name="seh_ports",
    service_name="Port %s",
    discovery_function=discover_seh_ports,
    check_function=check_seh_ports,
    check_default_parameters={},
)
