#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.hp_proliant import (
    check_hp_proliant_fans,
    inventory_hp_proliant_fans,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.hp_proliant import DETECT

check_info["hp_proliant_fans"] = {
    "detect": DETECT,
    "check_function": check_hp_proliant_fans,
    "discovery_function": inventory_hp_proliant_fans,
    "service_name": "HW FAN%s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.232.6.2.6.7.1",
        oids=["2", "3", "4", "6", "9", "12"],
    ),
}
