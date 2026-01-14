#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.dell_poweredge import check_dell_poweredge_status
from cmk.plugins.dell.lib import DETECT_IDRAC_POWEREDGE

check_info = {}


def discover_dell_poweredge_status(info):
    if info:
        return [(None, None)]
    return []


def parse_dell_poweredge_status(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_poweredge_status"] = LegacyCheckDefinition(
    name="dell_poweredge_status",
    parse_function=parse_dell_poweredge_status,
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5",
        oids=[
            "1.1.6.0",
            "1.2.2.0",
            "1.3.5.0",
            "1.3.12.0",
            "2.1.0",
            "4.300.10.1.11.1",
            "4.300.10.1.49.1",
        ],
    ),
    service_name="PowerEdge Health",
    discovery_function=discover_dell_poweredge_status,
    check_function=check_dell_poweredge_status,
)
