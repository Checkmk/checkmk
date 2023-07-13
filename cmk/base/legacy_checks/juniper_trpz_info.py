#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.juniper import DETECT_JUNIPER_TRPZ


def inventory_juniper_trpz_info(info):
    return [(None, None)]


def check_juniper_trpz_info(_no_item, _no_params, info):
    serial, version = info[0]
    message = "S/N: %s, FW Version: %s" % (serial, version)
    return 0, message


check_info["juniper_trpz_info"] = LegacyCheckDefinition(
    detect=DETECT_JUNIPER_TRPZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.2.1",
        oids=["1", "4"],
    ),
    service_name="Info",
    discovery_function=inventory_juniper_trpz_info,
    check_function=check_juniper_trpz_info,
)
