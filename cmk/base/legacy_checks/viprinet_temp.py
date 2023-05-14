#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.viprinet import DETECT_VIPRINET


def check_viprinet_temp(item, params, info):
    reading = int(info[0][item == "System"])
    return check_temperature(reading, params, "viprinet_temp_%s" % item)


check_info["viprinet_temp"] = LegacyCheckDefinition(
    detect=DETECT_VIPRINET,
    check_function=check_viprinet_temp,
    discovery_function=lambda info: len(info) > 0 and [("CPU", None), ("System", None)] or [],
    service_name="Temperature %s",
    check_ruleset_name="temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.2",
        oids=["3", "4"],
    ),
)
