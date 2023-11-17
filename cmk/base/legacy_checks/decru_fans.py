#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.decru import DETECT_DECRU

decru_fan_default_levels = (8000, 8400)


def inventory_decru_fans(info):
    return [(l[0], decru_fan_default_levels) for l in info]


def check_decru_fans(item, params, info):
    for fan_name, rpm in info:
        if fan_name == item:
            rpm = int(rpm)
            crit, warn = params
            perfdata = [("rpm", rpm, 0, None, warn, crit)]
            infotxt = "%d RPM" % rpm
            if rpm <= crit:
                return 2, infotxt, perfdata
            if rpm <= warn:
                return 1, infotxt, perfdata
            return 0, infotxt, perfdata

    return (3, "fan not found")


check_info["decru_fans"] = LegacyCheckDefinition(
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.2.3.1",
        oids=["2", "3"],
    ),
    service_name="FAN %s",
    discovery_function=inventory_decru_fans,
    check_function=check_decru_fans,
)
