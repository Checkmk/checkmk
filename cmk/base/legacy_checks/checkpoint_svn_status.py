#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.checkpoint import DETECT


def inventory_checkpoint_svn_status(info):
    if info:
        return [(None, None)]
    return []


def check_checkpoint_svn_status(item, params, info):
    if info:
        major, minor, code, description = info[0]
        ver = "v%s.%s" % (major, minor)
        if int(code) != 0:
            return 2, description
        return 0, "OK (%s)" % ver
    return None


check_info["checkpoint_svn_status"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_checkpoint_svn_status,
    discovery_function=inventory_checkpoint_svn_status,
    service_name="SVN Status",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6",
        oids=["2", "3", "101", "103"],
    ),
)
