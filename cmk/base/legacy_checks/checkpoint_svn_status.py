#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.checkpoint import DETECT


def inventory_checkpoint_svn_status(info):
    if info:
        return [(None, None)]
    return []


def check_checkpoint_svn_status(item, params, info):
    if info:
        major, minor, code, description = info[0]
        ver = f"v{major}.{minor}"
        if int(code) != 0:
            return 2, description
        return 0, "OK (%s)" % ver
    return None


def parse_checkpoint_svn_status(string_table: StringTable) -> StringTable:
    return string_table


check_info["checkpoint_svn_status"] = LegacyCheckDefinition(
    parse_function=parse_checkpoint_svn_status,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6",
        oids=["2", "3", "101", "103"],
    ),
    service_name="SVN Status",
    discovery_function=inventory_checkpoint_svn_status,
    check_function=check_checkpoint_svn_status,
)
