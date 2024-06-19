#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, savefloat
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.config import check_info

from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.lib.stulz import DETECT_STULZ


def inventory_stulz_humidity(info):
    return [(x[0], {}) for x in info]


def check_stulz_humidity(item, params, info):
    for line in info:
        if line[0] == item:
            return check_humidity(savefloat(line[1]) / 10, params)
    return None


def parse_stulz_humidity(string_table: StringTable) -> StringTable:
    return string_table


check_info["stulz_humidity"] = LegacyCheckDefinition(
    parse_function=parse_stulz_humidity,
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1.1194",
        oids=[OIDEnd(), "1"],
    ),
    service_name="Humidity %s ",
    discovery_function=inventory_stulz_humidity,
    check_function=check_stulz_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (60.0, 65.0),
        "levels_lower": (40.0, 35.0),
    },
)
