#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.huawei.lib import DETECT_HUAWEI_OSN

check_info = {}

# The laser should not get hotter than 70°C


def discover_huawei_osn_temp(info):
    for line in info:
        yield (line[1], {})


def check_huawei_osn_temp(item, params, info):
    for line in info:
        if item == line[1]:
            temp = float(line[0]) / 10.0
            yield check_temperature(temp, params, "huawei_osn_temp_%s" % item)


def parse_huawei_osn_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["huawei_osn_temp"] = LegacyCheckDefinition(
    name="huawei_osn_temp",
    parse_function=parse_huawei_osn_temp,
    detect=DETECT_HUAWEI_OSN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.2.25.3.40.50.76.10.1",
        oids=["2.190", "6.190"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_huawei_osn_temp,
    check_function=check_huawei_osn_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (70.0, 80.0),
    },
)
