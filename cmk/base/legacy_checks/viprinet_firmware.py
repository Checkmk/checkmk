#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.viprinet import DETECT_VIPRINET


def check_viprinet_firmware(_no_item, _no_params, info):
    fw_status_map = {
        "0": "No new firmware available",
        "1": "Update Available",
        "2": "Checking for Updates",
        "3": "Downloading Update",
        "4": "Installing Update",
    }
    fw_status = fw_status_map.get(info[0][1])
    if fw_status:
        return (0, "%s, %s" % (info[0][0], fw_status))
    return (3, "%s, no firmware status available")


check_info["viprinet_firmware"] = {
    "detect": DETECT_VIPRINET,
    "check_function": check_viprinet_firmware,
    "discovery_function": lambda info: len(info) > 0 and [(None, None)] or [],
    "service_name": "Firmware Version",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.35424.1.1",
        oids=["4", "7"],
    ),
}
