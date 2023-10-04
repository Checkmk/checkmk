#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.checkpoint import checkpoint_sensorstatus_to_nagios
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.checkpoint import DETECT


def format_item_checkpoint_temp(name):
    return name.upper().replace(" TEMP", "")


def inventory_checkpoint_temp(info):
    for name, _value, _unit, _dev_status in info:
        yield format_item_checkpoint_temp(name), {}


def check_checkpoint_temp(item, params, info):
    for name, value, unit, dev_status in info:
        if format_item_checkpoint_temp(name) == item:
            unit = unit.replace("degree", "").strip().lower()
            state, state_readable = checkpoint_sensorstatus_to_nagios[dev_status]

            if value == "":
                return state, "Status: %s" % state_readable

            return check_temperature(
                float(value),
                params,
                "checkpoint_temp_%s" % item,
                dev_unit=unit,
                dev_status=state,
                dev_status_name=state_readable,
            )
    return None


check_info["checkpoint_temp"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.8.1.1",
        oids=["2", "3", "4", "6"],
    ),
    service_name="Temperature %s",
    discovery_function=inventory_checkpoint_temp,
    check_function=check_checkpoint_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (50.0, 60.0)},
)
