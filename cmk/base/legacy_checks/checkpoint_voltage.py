#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.checkpoint import SENSOR_STATUS_TO_CMK_STATUS
from cmk.plugins.checkpoint.lib import DETECT

check_info = {}


def discover_checkpoint_voltage(info):
    for name, _value, _unit, _dev_status in info:
        yield name, {}


def check_checkpoint_voltage(item, params, info):
    for name, value, unit, dev_status in info:
        if name == item:
            state, state_readable = SENSOR_STATUS_TO_CMK_STATUS[dev_status]
            return state, f"Status: {state_readable}, {value} {unit}"
    return None


def parse_checkpoint_voltage(string_table: StringTable) -> StringTable:
    return string_table


check_info["checkpoint_voltage"] = LegacyCheckDefinition(
    name="checkpoint_voltage",
    parse_function=parse_checkpoint_voltage,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.8.3.1",
        oids=["2", "3", "4", "6"],
    ),
    service_name="Voltage %s",
    discovery_function=discover_checkpoint_voltage,
    check_function=check_checkpoint_voltage,
)
