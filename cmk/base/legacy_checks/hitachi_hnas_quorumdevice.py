#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.hitachi_hnas import DETECT


def inventory_hitachi_hnas_quorumdevice(info):
    return [(None, None)]


def check_hitachi_hnas_quorumdevice(item, _no_params, info):
    status = int(info[0][0])
    statusmap = (
        "unknown",
        "unconfigured",
        "offLine",
        "owned",
        "configured",
        "granted",
        "clusterNodeNotUp",
        "misconfigured",
    )
    if status >= len(statusmap):
        return 3, "Quorum Device reports unidentified status %s" % status

    if status == 4:
        rc = 0
    else:
        rc = 1
    return rc, "Quorum Device reports status %s" % statusmap[status]


check_info["hitachi_hnas_quorumdevice"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_hitachi_hnas_quorumdevice,
    discovery_function=inventory_hitachi_hnas_quorumdevice,
    service_name="Quorum Device",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.5",
        oids=["7"],
    ),
)
