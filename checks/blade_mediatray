#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.blade import DETECT_BLADE


def inventory_blade_mediatray(info):
    if len(info) == 1 and info[0][0] == "1":
        yield None, None


def check_blade_mediatray(_no_item, _no_params, info):
    if len(info) < 1:
        return (3, "no information about media tray in SNMP output")
    present = info[0][0]
    communicating = info[0][1]
    if present != "1":
        return (2, "media tray not present")
    if communicating != "1":
        return (2, "media tray not communicating")
    return (0, "media tray present and communicating")


check_info["blade_mediatray"] = {
    "detect": DETECT_BLADE,
    "check_function": check_blade_mediatray,
    "discovery_function": inventory_blade_mediatray,
    "service_name": "Media tray",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.2.2.5.2",
        oids=["74", "75"],
    ),
}
