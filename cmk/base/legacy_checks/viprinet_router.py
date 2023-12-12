#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.viprinet import DETECT_VIPRINET


def check_viprinet_router(_no_item, params, info):
    router_mode_map = {
        "0": "Node",
        "1": "Hub",
        "2": "Hub running as HotSpare",
        "3": "Hotspare-Hub replacing another router",
    }
    current_mode = info[0][0][0]
    mode = router_mode_map.get(current_mode)

    expect_mode = params.get("expect_mode")
    if expect_mode:
        # Requires mode found on inventory
        if expect_mode == "inv":
            expect_mode = params.get("mode_inv")
        if expect_mode in router_mode_map:
            if expect_mode != current_mode:
                return (
                    2,
                    f"Mode '{mode}' differs from expected mode '{router_mode_map.get(expect_mode)}'",
                )

    if mode:
        return (0, mode)
    return (3, "Undefined Mode")


check_info["viprinet_router"] = LegacyCheckDefinition(
    detect=DETECT_VIPRINET,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.1",
        oids=["5"],
    ),
    service_name="Router Mode",
    discovery_function=lambda info: len(info) > 0 and [(None, {"mode_inv": info[0][0][0]})] or [],
    check_function=check_viprinet_router,
    check_ruleset_name="viprinet_router",
)
