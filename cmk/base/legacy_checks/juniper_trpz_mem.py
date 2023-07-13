#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.juniper_mem import (
    check_juniper_mem_generic,
    inventory_juniper_mem_generic,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.juniper import DETECT_JUNIPER_TRPZ

check_info["juniper_trpz_mem"] = LegacyCheckDefinition(
    detect=DETECT_JUNIPER_TRPZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.8.1.1",
        oids=["12.1", "6"],
    ),
    service_name="Memory",
    discovery_function=inventory_juniper_mem_generic,
    check_function=check_juniper_mem_generic,
    check_ruleset_name="juniper_mem",
)
