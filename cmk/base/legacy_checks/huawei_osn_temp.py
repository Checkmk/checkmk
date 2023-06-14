#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.huawei import DETECT_HUAWEI_OSN

# The laser should not get hotter than 70°C


def inventory_huawei_osn_temp(info):
    for line in info:
        yield (line[1], {})


def check_huawei_osn_temp(item, params, info):
    for line in info:
        if item == line[1]:
            temp = float(line[0]) / 10.0
            yield check_temperature(temp, params, "huawei_osn_temp_%s" % item)


check_info["huawei_osn_temp"] = LegacyCheckDefinition(
    detect=DETECT_HUAWEI_OSN,
    discovery_function=inventory_huawei_osn_temp,
    check_function=check_huawei_osn_temp,
    service_name="Temperature %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.2.25.3.40.50.76.10.1",
        oids=["2.190", "6.190"],
    ),
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (70.0, 80.0),
    },
)
