#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.checkpoint import checkpoint_sensorstatus_to_nagios
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.checkpoint import DETECT


def inventory_checkpoint_voltage(info):
    for name, _value, _unit, _dev_status in info:
        yield name, {}


def check_checkpoint_voltage(item, params, info):
    for name, value, unit, dev_status in info:
        if name == item:
            state, state_readable = checkpoint_sensorstatus_to_nagios[dev_status]
            return state, "Status: %s, %s %s" % (state_readable, value, unit)
    return None


check_info["checkpoint_voltage"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_checkpoint_voltage,
    discovery_function=inventory_checkpoint_voltage,
    service_name="Voltage %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.8.3.1",
        oids=["2", "3", "4", "6"],
    ),
)
