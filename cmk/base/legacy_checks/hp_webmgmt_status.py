#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, exists, SNMPTree, startswith, StringTable

check_info = {}


def discover_hp_webmgmt_status(info):
    for index, _health in info[0]:
        yield index, None


def check_hp_webmgmt_status(item, _no_params, info):
    status_map = {
        "1": (3, "unknown"),
        "2": (3, "unused"),
        "3": (0, "ok"),
        "4": (1, "warning"),
        "5": (2, "critical"),
        "6": (2, "non-recoverable"),
    }

    device_model = info[1][0][0]
    serial_number = info[2][0][0]
    for index, health in info[0]:
        if index == item:
            status, status_msg = status_map[health]
            infotext = "Device status: %s" % status_msg
            if device_model and serial_number:
                infotext += f" [Model: {device_model}, Serial Number: {serial_number}]"
            return status, infotext
    return None


def parse_hp_webmgmt_status(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["hp_webmgmt_status"] = LegacyCheckDefinition(
    name="hp_webmgmt_status",
    parse_function=parse_hp_webmgmt_status,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11"),
        exists(".1.3.6.1.4.1.11.2.36.1.1.5.1.1.*"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.11.2.36.1.1.5.1.1",
            oids=["1", "3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.11.2.36.1.1.5.1.1.9",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.11.2.36.1.1.5.1.1.10",
            oids=["1"],
        ),
    ],
    service_name="Status %s",
    discovery_function=discover_hp_webmgmt_status,
    check_function=check_hp_webmgmt_status,
)
