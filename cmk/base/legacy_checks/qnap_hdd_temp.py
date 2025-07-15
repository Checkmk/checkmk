#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.qnap import DETECT_QNAP

check_info = {}


def parse_qnap_hdd_temp(string_table):
    parsed = {}
    for hdd, temp in string_table:
        try:
            temp = float(temp.split()[0])
            parsed[hdd] = temp
        except ValueError:
            pass
    return parsed


def check_qqnap_hdd_temp(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield check_temperature(reading=data, unique_name=item, params=params)


def discover_qnap_hdd_temp(section):
    yield from ((item, {}) for item in section)


check_info["qnap_hdd_temp"] = LegacyCheckDefinition(
    name="qnap_hdd_temp",
    detect=DETECT_QNAP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.24681.1.2.11.1",
        oids=["2", "3"],
    ),
    parse_function=parse_qnap_hdd_temp,
    service_name="QNAP %s Temperature",
    discovery_function=discover_qnap_hdd_temp,
    check_function=check_qqnap_hdd_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (40.0, 45.0),
    },
)
