#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


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


def check_viprinet_firmware(section: StringTable) -> CheckResult:
    fw_status_map = {
        "0": "No new firmware available",
        "1": "Update Available",
        "2": "Checking for Updates",
        "3": "Downloading Update",
        "4": "Installing Update",
    }
    fw_status = fw_status_map.get(section[0][1])
    if fw_status:
        yield Result(state=State.OK, summary=f"{section[0][0]}, {fw_status}")
        return
    yield Result(state=State.UNKNOWN, summary=f"{section[0][0]}, No firmware status available")
    return


def parse_viprinet_firmware(string_table: StringTable) -> StringTable:
    return string_table


def discover_viprinet_firmware(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


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
