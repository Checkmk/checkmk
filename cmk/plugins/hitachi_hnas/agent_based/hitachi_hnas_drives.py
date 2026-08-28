#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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
from cmk.plugins.hitachi_hnas.lib import DETECT

Section = Mapping[str, int]

_STATUS_MAP = (
    ("Online", State.OK),
    ("MBR corrupt", State.CRIT),
    ("Failed and unaccessible", State.CRIT),
    ("Not present", State.CRIT),
    ("Not accessible by controller", State.CRIT),
    ("Offline", State.CRIT),
    ("Initializing", State.CRIT),
    ("Formatting", State.CRIT),
    ("Unknown", State.UNKNOWN),
)


def parse_hitachi_hnas_drives(string_table: StringTable) -> Section:
    section: dict[str, int] = {}
    for (status,) in string_table:
        section.setdefault(status, 0)
        section[status] += 1
    return section


def discover_hitachi_hnas_drives(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_hitachi_hnas_drives(section: Section) -> CheckResult:
    for status, count in section.items():
        name, state = _STATUS_MAP[int(status) - 1]
        yield Result(state=state, summary=f"{name}: {count}")


snmp_section_hitachi_hnas_drives = SimpleSNMPSection(
    name="hitachi_hnas_drives",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.3.4.2.1",
        oids=["4"],
    ),
    parse_function=parse_hitachi_hnas_drives,
)


check_plugin_hitachi_hnas_drives = CheckPlugin(
    name="hitachi_hnas_drives",
    service_name="System Drives",
    discovery_function=discover_hitachi_hnas_drives,
    check_function=check_hitachi_hnas_drives,
)
