#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.stulz import DETECT_STULZ


def inventory_stulz_alerts(info):
    return [(x[0], None) for x in info]


def check_stulz_alerts(item, _no_params, info):
    for line in info:
        if line[0] == item:
            if line[1] != "0":
                return 2, "Device is in alert state"
            return 0, "No alerts on device"
    return 3, "No information found about the device"


check_info["stulz_alerts"] = LegacyCheckDefinition(
    detect=DETECT_STULZ,
    check_function=check_stulz_alerts,
    discovery_function=inventory_stulz_alerts,
    service_name="Alerts %s ",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.4.4.1.1.1.1010",
        oids=[OIDEnd(), "1"],
    ),
)
