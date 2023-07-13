#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.blade import DETECT_BLADE

# Example excerpt from SNMP data:
# .1.3.6.1.4.1.2.3.51.2.2.7.1.0  255
# .1.3.6.1.4.1.2.3.51.2.2.7.2.1.1.1  1
# .1.3.6.1.4.1.2.3.51.2.2.7.2.1.2.1  "Good"
# .1.3.6.1.4.1.2.3.51.2.2.7.2.1.3.1  "No critical or warning events"
# .1.3.6.1.4.1.2.3.51.2.2.7.2.1.4.1  "No timestamp"


def inventory_blade_health(info):
    if len(info) == 1:
        return [(None, None)]
    return []


def check_blade_health(_no_item, _no_params, info):
    state = info[0][0]
    descr = ": " + ", ".join([line[1] for line in info if len(line) > 1])

    if state == "255":
        return (0, "State is good")
    if state == "2":
        return (1, "State is degraded (non critical)" + descr)
    if state == "4":
        return (1, "State is degraded (system level)" + descr)
    if state == "0":
        return (2, "State is critical!" + descr)
    return (3, "Undefined state code %s%s" % (state, descr))


check_info["blade_health"] = LegacyCheckDefinition(
    detect=DETECT_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.2.2.7",
        oids=["1.0", "2.1.3.1"],
    ),
    service_name="Summary health state",
    discovery_function=inventory_blade_health,
    check_function=check_blade_health,
)
