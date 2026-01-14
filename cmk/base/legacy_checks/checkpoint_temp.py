#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.checkpoint import SENSOR_STATUS_TO_CMK_STATUS
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.checkpoint.lib import DETECT

check_info = {}


def format_item_checkpoint_temp(name):
    return name.upper().replace(" TEMP", "")


def discover_checkpoint_temp(info):
    for name, _value, _unit, _dev_status in info:
        yield format_item_checkpoint_temp(name), {}


def check_checkpoint_temp(item, params, info):
    for name, value, unit, dev_status in info:
        if format_item_checkpoint_temp(name) == item:
            unit = unit.replace("degree", "").strip().lower()
            state, state_readable = SENSOR_STATUS_TO_CMK_STATUS[dev_status]

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


def parse_checkpoint_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["checkpoint_temp"] = LegacyCheckDefinition(
    name="checkpoint_temp",
    parse_function=parse_checkpoint_temp,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.8.1.1",
        oids=["2", "3", "4", "6"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_checkpoint_temp,
    check_function=check_checkpoint_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (50.0, 60.0)},
)
