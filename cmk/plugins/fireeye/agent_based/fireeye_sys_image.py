#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.fireeye.lib import DETECT

# .1.3.6.1.4.1.25597.11.5.1.1.0 eMPS (eMPS) 7.6.5.442663 --> FE-FIREEYE-MIB::feInstalledSystemImage.0
# .1.3.6.1.4.1.25597.11.5.1.2.0 7.6.5 --> FE-FIREEYE-MIB::feSystemImageVersionCurrent.0
# .1.3.6.1.4.1.25597.11.5.1.3.0 7.6.5 --> FE-FIREEYE-MIB::feSystemImageVersionLatest.0
# .1.3.6.1.4.1.25597.11.5.1.4.0 1 --> FE-FIREEYE-MIB::feIsSystemImageLatest.0


def check_fireeye_sys_image(section: StringTable) -> CheckResult:
    installed, version, latest_version, is_latest = section[0]
    state = State.OK
    infotext = f"Image: {installed}, Version: {version}"

    if is_latest != "1":
        state = State.WARN
        infotext += f", Latest version: {latest_version}"

    yield Result(state=state, summary=infotext)


def parse_fireeye_sys_image(string_table: StringTable) -> StringTable:
    return string_table


def discover_fireeye_sys_image(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


snmp_section_fireeye_sys_image = SimpleSNMPSection(
    name="fireeye_sys_image",
    parse_function=parse_fireeye_sys_image,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.5.1",
        oids=["1", "2", "3", "4"],
    ),
)


check_plugin_fireeye_sys_image = CheckPlugin(
    name="fireeye_sys_image",
    service_name="System image",
    discovery_function=discover_fireeye_sys_image,
    check_function=check_fireeye_sys_image,
)
