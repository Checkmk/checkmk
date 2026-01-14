#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.brocade.lib import DETECT_MLX

check_info = {}


def parse_brocade_mlx_temp(string_table):
    parsed = {}
    for temp_descr, temp_value in string_table:
        if temp_value and temp_value != "0":
            item = (
                temp_descr.replace("temperature", "")
                .replace("module", "Module")
                .replace("sensor", "Sensor")
                .replace(",", "")
                .strip()
            )
            parsed[item] = float(temp_value) * 0.5
    return parsed


def discover_brocade_mlx_temp(parsed):
    for item in parsed:
        yield item, {}


def check_brocade_mlx_temp(item, params, parsed):
    if item in parsed:
        return check_temperature(parsed[item], params, "brocade_mlx_temp_%s" % item)
    if "Module" in item and "Sensor" not in item:
        # item discovered in 1.2.6 had the sensor-id stripped and module id replaced
        # so it's impossible to look by that name
        return 3, "check had an incompatible change, please re-discover this host"
    return None


check_info["brocade_mlx_temp"] = LegacyCheckDefinition(
    name="brocade_mlx_temp",
    detect=DETECT_MLX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1991.1.1.2.13.1.1",
        oids=["3", "4"],
    ),
    parse_function=parse_brocade_mlx_temp,
    service_name="Temperature %s",
    discovery_function=discover_brocade_mlx_temp,
    check_function=check_brocade_mlx_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (105.0, 110.0)},
)
