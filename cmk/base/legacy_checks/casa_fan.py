#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.lib.casa import DETECT_CASA


def inventory_casa_fan(info):
    inventory = []
    for nr, _speed in info[0]:
        inventory.append((nr, None))
    return inventory


def check_casa_fan(item, _no_params, info):
    for idx, (nr, speed) in enumerate(info[0]):
        if item == nr:
            fan_status = info[1][idx][1]
            if fan_status == "1":
                return (0, "%s RPM" % speed)
            if fan_status == "3":
                return (1, "%s RPM, running over threshold (!)" % speed)
            if fan_status == "2":
                return (1, "%s RPM, running under threshold (!)" % speed)
            if fan_status == "0":
                return (3, "%s RPM, unknown fan status (!)" % speed)
            if fan_status == "4":
                return (2, "FAN Failure (!!)")
    return (3, "Fan %s not found in snmp output" % item)


def parse_casa_fan(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["casa_fan"] = LegacyCheckDefinition(
    parse_function=parse_casa_fan,
    detect=DETECT_CASA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.20858.10.31.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.20858.10.33.1.4.1",
            oids=[OIDEnd(), "4"],
        ),
    ],
    service_name="Fan %s",
    discovery_function=inventory_casa_fan,
    check_function=check_casa_fan,
)
