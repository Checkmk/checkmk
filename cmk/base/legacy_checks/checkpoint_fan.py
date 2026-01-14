#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.checkpoint import SENSOR_STATUS_TO_CMK_STATUS
from cmk.plugins.checkpoint.lib import DETECT

check_info = {}


def format_item_checkpoint_fan(name):
    return name.replace(" Fan", "")


def discover_checkpoint_fan(info):
    for name, _value, _unit, _dev_status in info:
        yield format_item_checkpoint_fan(name), {}


def check_checkpoint_fan(item, params, info):
    for name, value, unit, dev_status in info:
        if format_item_checkpoint_fan(name) == item:
            state, state_readable = SENSOR_STATUS_TO_CMK_STATUS[dev_status]
            yield state, f"Status: {state_readable}, {value} {unit}"


def parse_checkpoint_fan(string_table: StringTable) -> StringTable:
    return string_table


check_info["checkpoint_fan"] = LegacyCheckDefinition(
    name="checkpoint_fan",
    parse_function=parse_checkpoint_fan,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.8.2.1",
        oids=["2", "3", "4", "6"],
    ),
    service_name="Fan %s",
    discovery_function=discover_checkpoint_fan,
    check_function=check_checkpoint_fan,
)
