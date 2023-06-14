#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.apc import DETECT


def inventory_apc_humidity(info):
    for line in info:
        if int(line[1]) >= 0:
            yield line[0], {}


def check_apc_humidity(item, params, info):
    for line in info:
        if line[0] == item:
            return check_humidity(saveint(line[1]), params)
    return None


check_info["apc_humidity"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_apc_humidity,
    discovery_function=inventory_apc_humidity,
    service_name="Humidity %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.10.4.2.3.1",
        oids=["3", "6"],
    ),
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (40, 35),
        "levels_lower": (60, 65),
    },
)
