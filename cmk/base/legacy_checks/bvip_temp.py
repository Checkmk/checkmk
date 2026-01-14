#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.bvip.lib import DETECT_BVIP

check_info = {}


def discover_bvip_temp(info):
    for line in info:
        # line[0] contains nice names like "CPU" and "System"
        yield line[0], {}


def check_bvip_temp(item, params, info):
    for nr, value in info:
        if nr == item:
            degree_celsius = float(value) / 10
            return check_temperature(degree_celsius, params, "bvip_temp_%s" % item)
    return None


def parse_bvip_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["bvip_temp"] = LegacyCheckDefinition(
    name="bvip_temp",
    parse_function=parse_bvip_temp,
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1.7.1",
        oids=[OIDEnd(), "1"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_bvip_temp,
    check_function=check_bvip_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (50.0, 60.0)},
)
