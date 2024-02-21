#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_OPENMANAGE


def inventory_dell_om_esmlog(info):
    if len(info) > 0:
        return [(None, None)]
    return []


def check_dell_om_esmlog(_no_item, _no_params, info):
    status = int(info[0][0])
    if status == 5:
        state = 2
        message = "ESM Log is full"
    elif status == 3:
        state = 0
        message = "EMS Log is less than 80% full"
    else:
        state = 1
        message = "EMS log more than 80% full"

    return state, message


def parse_dell_om_esmlog(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_om_esmlog"] = LegacyCheckDefinition(
    parse_function=parse_dell_om_esmlog,
    detect=DETECT_OPENMANAGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.1.200.10.1.41",
        oids=["1"],
    ),
    service_name="ESM Log",
    discovery_function=inventory_dell_om_esmlog,
    check_function=check_dell_om_esmlog,
)
