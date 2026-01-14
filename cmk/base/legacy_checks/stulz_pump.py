#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.stulz.lib import DETECT_STULZ

check_info = {}


def discover_stulz_pump(info):
    inventory = []
    for pump_id, _pump_status in info[0]:
        pump_id = pump_id.replace(".1", "")
        inventory.append((pump_id, None))
    return inventory


def check_stulz_pump(item, _no_params, info):
    for index, (pump_id, pump_status) in enumerate(info[0]):
        pump_id = pump_id.replace(".1", "")
        if pump_id == item:
            pump_rpm = info[1][index][0]
            perfdata = [("rpm", pump_rpm + "%", None, None, 0, 100)]
            if pump_status == "1":
                state = 0
                infotext = "Pump is running at %s%%" % pump_rpm
            elif pump_status == "0":
                state = 2
                infotext = "Pump is not running"
            else:
                state = 3
                infotext = "Pump reports unidentified status " + pump_status
            return state, infotext, perfdata
    return 3, "Pump %s not found" % item


def parse_stulz_pump(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["stulz_pump"] = LegacyCheckDefinition(
    name="stulz_pump",
    parse_function=parse_stulz_pump,
    detect=DETECT_STULZ,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.29462.10.2.1.1.2.1.4.1.1.5802",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.29462.10.2.1.1.2.1.4.1.1.5821",
            oids=["2"],
        ),
    ],
    service_name="Pump %s",
    discovery_function=discover_stulz_pump,
    check_function=check_stulz_pump,
)
