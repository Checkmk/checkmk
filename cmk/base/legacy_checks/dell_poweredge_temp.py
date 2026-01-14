#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.dell_poweredge import (
    check_dell_poweredge_temp,
    dell_poweredge_temp_makeitem,
)
from cmk.plugins.dell.lib import DETECT_IDRAC_POWEREDGE

check_info = {}


def discover_dell_poweredge_temp(info):
    for line in info:
        if line[2] != "1":  # StateSettings not 'unknown'
            item = dell_poweredge_temp_makeitem(line[0], line[1], line[5])
            yield item, {}


def parse_dell_poweredge_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_poweredge_temp"] = LegacyCheckDefinition(
    name="dell_poweredge_temp",
    parse_function=parse_dell_poweredge_temp,
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.4.700.20.1",
        oids=["1", "2", "4", "5", "6", "8", "10", "11", "12", "13"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_dell_poweredge_temp,
    check_function=check_dell_poweredge_temp,
    check_ruleset_name="temperature",
)
