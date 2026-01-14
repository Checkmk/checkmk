#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.huawei.lib import DETECT_HUAWEI_OSN

check_info = {}

# The typical OSN power unit delivers 750 W max


def discover_huawei_osn_power(info):
    for line in info:
        yield (line[0], None)


def check_huawei_osn_power(item, params, info):
    for line in info:
        if item == line[0]:
            state = 0
            reading = int(line[1])
            warn, crit = params["levels"]

            yield 0, "Current reading: %s W" % reading, [("power", reading, warn, crit, 0)]

            if reading >= crit:
                state = 2
            elif reading >= warn:
                state = 1

            if state:
                yield state, f"(warn/crit at {warn}/{crit} W)"


def parse_huawei_osn_power(string_table: StringTable) -> StringTable:
    return string_table


check_info["huawei_osn_power"] = LegacyCheckDefinition(
    name="huawei_osn_power",
    parse_function=parse_huawei_osn_power,
    detect=DETECT_HUAWEI_OSN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.2.25.4.70.20.20.10.1",
        oids=["1", "2"],
    ),
    service_name="Unit %s (Power)",
    discovery_function=discover_huawei_osn_power,
    check_function=check_huawei_osn_power,
    check_default_parameters={
        "levels": (700, 730),
    },
)
