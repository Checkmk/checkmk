#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.ibm import DETECT_IBM_IMM


def inventory_ibm_imm_health(info):
    if info:
        return [(None, None)]
    return []


def check_ibm_imm_health(_no_item, _no_params, info):
    if not info or not info[0]:
        return 3, "Health info not found in SNMP data"

    num_alerts = int((len(info) - 1) / 3)
    infotext = ""
    for i in range(0, num_alerts):
        state = info[num_alerts + 1 + i][0]
        text = info[num_alerts * 2 + 1 + i][0]
        if infotext != "":
            infotext += ", "
        infotext += "%s(%s)" % (text, state)

    state = info[0][0]
    if state == "255":
        return (0, "no problem found")
    if state == "0":
        return (2, infotext + " - manual log clearing needed to recover state")
    if state == "2":
        return (2, infotext)
    if state == "4":
        return (1, infotext)
    return (3, infotext)


check_info["ibm_imm_health"] = LegacyCheckDefinition(
    detect=DETECT_IBM_IMM,
    check_function=check_ibm_imm_health,
    discovery_function=inventory_ibm_imm_health,
    service_name="System health",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.3.1",
        oids=["4"],
    ),
)
