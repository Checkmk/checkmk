#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.juniper.lib import DETECT_JUNIPER_SCREENOS

check_info = {}


def discover_juniper_screenos_temp(info):
    for name, _temp in info:
        if name.endswith("Temperature"):
            name = name.rsplit(None, 1)[0]
        yield name, {}


def check_juniper_screenos_temp(item, params, info):
    for name, temp in info:
        if name.endswith("Temperature"):
            name = name.rsplit(None, 1)[0]
        if name == item:
            return check_temperature(int(temp), params, "juniper_screenos_temp_%s" % item)
    return None


def parse_juniper_screenos_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["juniper_screenos_temp"] = LegacyCheckDefinition(
    name="juniper_screenos_temp",
    parse_function=parse_juniper_screenos_temp,
    detect=DETECT_JUNIPER_SCREENOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3224.21.4.1",
        oids=["4", "3"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_juniper_screenos_temp,
    check_function=check_juniper_screenos_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (70.0, 80.0)},
)
