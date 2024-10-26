#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.viprinet import DETECT_VIPRINET

check_info = {}


def check_viprinet_firmware(_no_item, _no_params, info):
    fw_status_map = {
        "0": "No new firmware available",
        "1": "Update Available",
        "2": "Checking for Updates",
        "3": "Downloading Update",
        "4": "Installing Update",
    }
    fw_status = fw_status_map.get(info[0][1])
    if fw_status:
        return (0, f"{info[0][0]}, {fw_status}")
    return (3, "%s, no firmware status available")


def parse_viprinet_firmware(string_table: StringTable) -> StringTable:
    return string_table


def discover_viprinet_firmware(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


check_info["viprinet_firmware"] = LegacyCheckDefinition(
    name="viprinet_firmware",
    parse_function=parse_viprinet_firmware,
    detect=DETECT_VIPRINET,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.1",
        oids=["4", "7"],
    ),
    service_name="Firmware Version",
    discovery_function=discover_viprinet_firmware,
    check_function=check_viprinet_firmware,
)
