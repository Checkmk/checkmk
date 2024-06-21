#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.bvip import DETECT_BVIP


def inventory_bvip_video_alerts(info):
    for cam, _alerts in info:
        yield cam.replace("\x00", ""), None


def check_bvip_video_alerts(item, _no_params, info):
    for cam, alerts in info:
        if cam.replace("\x00", "") == item:
            if alerts != "0":
                return 2, "Device on Alarm State"
            return 0, "No alarms"
    return None


def parse_bvip_video_alerts(string_table: StringTable) -> StringTable:
    return string_table


check_info["bvip_video_alerts"] = LegacyCheckDefinition(
    parse_function=parse_bvip_video_alerts,
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1",
        oids=["1.1.3.1", "3.1.1"],
    ),
    service_name="Video Alerts",
    discovery_function=inventory_bvip_video_alerts,
    check_function=check_bvip_video_alerts,
)
