#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.juniper.lib import DETECT_JUNIPER_TRPZ


class Section(NamedTuple):
    serial: str
    version: str


def discover_juniper_trpz_info(section: Section) -> DiscoveryResult:
    yield Service()


def check_juniper_trpz_info(section: Section) -> CheckResult:
    message = f"S/N: {section.serial}, FW Version: {section.version}"
    yield Result(state=State.OK, summary=message)


def parse_juniper_trpz_info(string_table: StringTable) -> Section | None:
    if len(string_table) == 0:
        return None
    serial, version = string_table[0]
    return Section(serial=serial, version=version)


snmp_section_juniper_trpz_info = SimpleSNMPSection(
    name="juniper_trpz_info",
    parse_function=parse_juniper_trpz_info,
    detect=DETECT_JUNIPER_TRPZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.2.1",
        oids=["1", "4"],
    ),
)


check_plugin_juniper_trpz_info = CheckPlugin(
    name="juniper_trpz_info",
    service_name="Info",
    discovery_function=discover_juniper_trpz_info,
    check_function=check_juniper_trpz_info,
)
