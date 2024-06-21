#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.brocade import DETECT_MLX


def brocade_mlx_fan_combine_item(id_, descr):
    if descr == "" or "(RPM " in descr:
        return id_
    return f"{id_} {descr}"


def inventory_brocade_mlx_fan(info):
    inventory = []
    for fan_id, fan_descr, fan_state in info:
        # Only add Fans who are present
        if fan_state != "1":
            inventory.append((brocade_mlx_fan_combine_item(fan_id, fan_descr), None))
    return inventory


def check_brocade_mlx_fan(item, _no_params, info):
    for fan_id, fan_descr, fan_state in info:
        if brocade_mlx_fan_combine_item(fan_id, fan_descr) == item:
            if fan_state == "2":
                return 0, "Fan reports state: normal"
            if fan_state == "3":
                return 2, "Fan reports state: failure"
            if fan_state == "1":
                return 3, "Fan reports state: other"
            return 3, "Fan reports an unhandled state (%s)" % fan_state
    return 3, "Fan not found"


def parse_brocade_mlx_fan(string_table: StringTable) -> StringTable:
    return string_table


check_info["brocade_mlx_fan"] = LegacyCheckDefinition(
    parse_function=parse_brocade_mlx_fan,
    detect=DETECT_MLX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1991.1.1.1.3.1.1",
        oids=["1", "2", "3"],
    ),
    service_name="Fan %s",
    discovery_function=inventory_brocade_mlx_fan,
    check_function=check_brocade_mlx_fan,
)
