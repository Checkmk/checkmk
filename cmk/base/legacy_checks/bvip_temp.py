#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.bvip import DETECT_BVIP


def inventory_bvip_temp(info):
    for line in info:
        # line[0] contains nice names like "CPU" and "System"
        yield line[0], {}


def check_bvip_temp(item, params, info):
    for nr, value in info:
        if nr == item:
            degree_celsius = float(value) / 10
            return check_temperature(degree_celsius, params, "bvip_temp_%s" % item)
    return None


check_info["bvip_temp"] = LegacyCheckDefinition(
    detect=DETECT_BVIP,
    check_function=check_bvip_temp,
    discovery_function=inventory_bvip_temp,
    service_name="Temperature %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1.7.1",
        oids=[OIDEnd(), "1"],
    ),
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (50.0, 60.0)},
)
