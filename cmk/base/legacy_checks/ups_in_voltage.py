#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.ups_in_voltage import check_ups_in_voltage

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.lib.ups import DETECT_UPS_GENERIC

check_info = {}


def discover_ups_in_voltage(info):
    yield from ((item, {}) for item, value in info if int(value) > 0)


def parse_ups_in_voltage(string_table: StringTable) -> StringTable:
    return string_table


check_info["ups_in_voltage"] = LegacyCheckDefinition(
    name="ups_in_voltage",
    parse_function=parse_ups_in_voltage,
    detect=DETECT_UPS_GENERIC,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1.3.3.1",
        oids=[OIDEnd(), "3"],
    ),
    service_name="IN voltage phase %s",
    discovery_function=discover_ups_in_voltage,
    check_function=check_ups_in_voltage,
    check_ruleset_name="evolt",
    check_default_parameters={
        "levels_lower": (210.0, 180.0),
    },
)
