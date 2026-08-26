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
from cmk.plugins.viprinet.lib import DETECT_VIPRINET


def parse_viprinet_firmware(string_table: StringTable) -> StringTable:
    return string_table


def discover_viprinet_firmware(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_viprinet_firmware(section: StringTable) -> CheckResult:
    name, status = section[0][0], section[0][1]

    match status:
        case "0":
            yield Result(state=State.OK, summary=f"{name}, No new firmware available")
        case "1":
            yield Result(state=State.OK, summary=f"{name}, Update Available")
        case "2":
            yield Result(state=State.OK, summary=f"{name}, Checking for Updates")
        case "3":
            yield Result(state=State.OK, summary=f"{name}, Downloading Update")
        case "4":
            yield Result(state=State.OK, summary=f"{name}, Installing Update")
        case _:
            yield Result(state=State.UNKNOWN, summary=f"{name}, No firmware status available")


snmp_section_viprinet_firmware = SimpleSNMPSection(
    name="viprinet_firmware",
    detect=DETECT_VIPRINET,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.1",
        oids=["4", "7"],
    ),
    parse_function=parse_viprinet_firmware,
)


check_plugin_viprinet_firmware = CheckPlugin(
    name="viprinet_firmware",
    service_name="Firmware Version",
    discovery_function=discover_viprinet_firmware,
    check_function=check_viprinet_firmware,
)
