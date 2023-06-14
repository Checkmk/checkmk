#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.hitachi_hnas import DETECT


def inventory_hitachi_hnas_drives(info):
    if info:
        return [(None, None)]
    return []


def parse_hitachi_hnas_drives(info):
    parsed = {}
    for (status,) in info:
        parsed.setdefault(status, 0)
        parsed[status] += 1
    return parsed


def check_hitachi_hnas_drives(_no_item, params, info):
    status_map = (
        ("Online", 0),
        ("MBR corrupt", 2),
        ("Failed and unaccessible", 2),
        ("Not present", 2),
        ("Not accessible by controller", 2),
        ("Offline", 2),
        ("Initializing", 2),
        ("Formatting", 2),
        ("Unknown", 3),
    )
    for status, count in info.items():
        infotext = "%s: %d" % (status_map[int(status) - 1][0], count)
        yield status_map[int(status) - 1][1], infotext


check_info["hitachi_hnas_drives"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_hitachi_hnas_drives,
    discovery_function=inventory_hitachi_hnas_drives,
    parse_function=parse_hitachi_hnas_drives,
    service_name="System Drives",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.3.4.2.1",
        oids=["4"],
    ),
)
