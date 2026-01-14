#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.viprinet.lib import DETECT_VIPRINET

check_info = {}


def discover_viprinet_serial(info):
    if info:
        return [(None, None)]
    return []


def check_viprinet_serial(_no_item, _no_params, info):
    return 0, info[0][0]


def parse_viprinet_serial(string_table: StringTable) -> StringTable:
    return string_table


check_info["viprinet_serial"] = LegacyCheckDefinition(
    name="viprinet_serial",
    parse_function=parse_viprinet_serial,
    detect=DETECT_VIPRINET,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.1",
        oids=["2"],
    ),
    service_name="Serial Number",
    discovery_function=discover_viprinet_serial,
    check_function=check_viprinet_serial,
)
