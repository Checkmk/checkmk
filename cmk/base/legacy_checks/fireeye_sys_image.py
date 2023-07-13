#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.fireeye import inventory_fireeye_generic
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.fireeye import DETECT

# .1.3.6.1.4.1.25597.11.5.1.1.0 eMPS (eMPS) 7.6.5.442663 --> FE-FIREEYE-MIB::feInstalledSystemImage.0
# .1.3.6.1.4.1.25597.11.5.1.2.0 7.6.5 --> FE-FIREEYE-MIB::feSystemImageVersionCurrent.0
# .1.3.6.1.4.1.25597.11.5.1.3.0 7.6.5 --> FE-FIREEYE-MIB::feSystemImageVersionLatest.0
# .1.3.6.1.4.1.25597.11.5.1.4.0 1 --> FE-FIREEYE-MIB::feIsSystemImageLatest.0


def check_fireeye_sys_image(_no_item, _no_params, info):
    installed, version, latest_version, is_latest = info[0]
    state = 0
    infotext = "Image: %s, Version: %s" % (installed, version)

    if is_latest != "1":
        state = 1
        infotext += ", Latest version: %s" % latest_version

    return state, infotext


check_info["fireeye_sys_image"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.5.1",
        oids=["1", "2", "3", "4"],
    ),
    service_name="System image",
    discovery_function=lambda info: inventory_fireeye_generic(info, False),
    check_function=check_fireeye_sys_image,
)
