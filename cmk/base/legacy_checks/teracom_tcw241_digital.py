#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import (
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import contains, SNMPTree, StringTable

check_info = {}


def parse_tcw241_digital(string_table: StringTable) -> Mapping[str, Mapping[str, str]]:
    """
    parse string_table data and create list of namedtuples for 4 digital sensors.

    expected string_table structure:
        list of digital sensor descriptions and states:
            [description1, description2, description3, description4]
            [input state1, input state2, input state3, input state4]

    converted to dictionary:
        {
            1: { description1: state1 }
            ...
            4: { description4: state4 }
        }

    :param string_table: parsed snmp data
    :return: list of namedtuples for digital sensors
    """
    try:
        descriptions, states = string_table[0][0], string_table[1][0]
    except IndexError:
        return {}

    info_dict: dict[str, dict[str, str]] = {}
    for index, (description, state) in enumerate(zip(descriptions, states)):
        # if state is '1', the sensor is 'open'
        sensor_state = "open" if state == "1" else "closed"

        info_dict[str(index + 1)] = {"description": description, "state": sensor_state}
    return info_dict


def check_tcw241_digital(
    item: str, params: Mapping[str, Any], parsed: Mapping[str, Mapping[str, str]]
) -> LegacyCheckResult:
    """
    Check sensor if it is open or closed

    :param item: sensor number
    :param params: <not used>
    :param info_dict: dictionary with digital sensor description and state (open/close)
    :return: status
    """
    if not (info_dict := parsed.get(item)):
        return
    yield (
        0 if info_dict.get("state") == "open" else 2,
        "[{}] is {}".format(
            info_dict.get("description"),
            info_dict.get("state"),
        ),
    )


def discover_teracom_tcw241_digital(
    section: Mapping[str, Mapping[str, str]],
) -> LegacyDiscoveryResult:
    yield from ((item, {}) for item in section)


check_info["teracom_tcw241_digital"] = LegacyCheckDefinition(
    name="teracom_tcw241_digital",
    detect=contains(".1.3.6.1.2.1.1.1.0", "Teracom"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.38783.3.2.2.3",
            oids=["1.0", "2.0", "3.0", "4.0"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.38783.3.3.3",
            oids=["1.0", "2.0", "3.0", "4.0"],
        ),
    ],
    parse_function=parse_tcw241_digital,
    service_name="Digital Sensor %s",
    discovery_function=discover_teracom_tcw241_digital,
    check_function=check_tcw241_digital,
)
