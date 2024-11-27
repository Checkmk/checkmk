#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.fireeye import DETECT

check_info = {}

# .1.3.6.1.4.1.25597.13.1.41.0 0
# .1.3.6.1.4.1.25597.13.1.42.0 0
# .1.3.6.1.4.1.25597.13.1.43.0 0


def discover_bypass(section: StringTable) -> DiscoveryResult:
    if section:
        value = int(section[0][0])
        yield Service(parameters={"value": value})


def check_fireeye_bypass(_no_item, params, info):
    expected_value = params.get("value", 0)
    current_value = int(info[0][0])
    yield 0, "Bypass E-Mail count: %d" % current_value
    if current_value != expected_value:
        yield 2, " (was %d before)" % expected_value


def parse_fireeye_bypass(string_table: StringTable) -> StringTable:
    return string_table


check_info["fireeye_bypass"] = LegacyCheckDefinition(
    name="fireeye_bypass",
    parse_function=parse_fireeye_bypass,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1",
        oids=["41"],
    ),
    service_name="Bypass Mail Rate",
    discovery_function=discover_bypass,
    check_function=check_fireeye_bypass,
)
