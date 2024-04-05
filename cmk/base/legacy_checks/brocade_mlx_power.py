#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.brocade import DETECT_MLX


def parse_brocade_mlx_power(string_table):
    parsed = {}

    if len(string_table[1]) > 0:
        # .1.3.6.1.4.1.1991.1.1.1.2.2.1
        for power_id, power_desc, power_state in string_table[1]:
            if power_state != "1":
                parsed[power_id] = {"desc": power_desc, "state": power_state}
    else:
        # .1.3.6.1.4.1.1991.1.1.1.2.1.1
        for power_id, power_desc, power_state in string_table[0]:
            if power_state != "1":
                parsed[power_id] = {"desc": power_desc, "state": power_state}
    return parsed


def inventory_brocade_mlx_power(parsed):
    inventory = []

    for powersupply_id in parsed:
        inventory.append((powersupply_id, None))
    return inventory


def check_brocade_mlx_power(item, _no_params, parsed):
    if item not in parsed:
        yield 3, "Power supply not found"

    for powersupply_id, powersupply_data in parsed.items():
        if powersupply_id == item:
            if powersupply_data["state"] == "2":
                yield 0, "Power supply reports state: normal"
            elif powersupply_data["state"] == "3":
                yield 2, "Power supply reports state: failure"
            elif powersupply_data["state"] == "1":
                yield 3, "Power supply reports state: other"
            else:
                yield 3, "Power supply reports an unhandled state (%s)" % powersupply_data["state"]


check_info["brocade_mlx_power"] = LegacyCheckDefinition(
    detect=DETECT_MLX,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.1.2.1.1",
            oids=["1", "2", "3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.1.2.2.1",
            oids=["2", "3", "4"],
        ),
    ],
    parse_function=parse_brocade_mlx_power,
    service_name="Power supply %s",
    discovery_function=inventory_brocade_mlx_power,
    check_function=check_brocade_mlx_power,
)
