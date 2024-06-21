#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.check_legacy_includes.ups_out_voltage import check_ups_out_voltage
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.ups_socomec import DETECT_SOCOMEC


def inventory_socomec_ups_out_voltage(info):
    if len(info) > 0:
        return [(x[0], {}) for x in info if int(x[1]) > 0]
    return []


def check_socomec_ups_out_voltage(item, params, info):
    conv_info = []
    for line in info:
        conv_info.append([line[0], saveint(line[1]) // 10, line[1]])
    return check_ups_out_voltage(item, params, conv_info)


def parse_ups_socomec_out_voltage(string_table: StringTable) -> StringTable:
    return string_table


check_info["ups_socomec_out_voltage"] = LegacyCheckDefinition(
    parse_function=parse_ups_socomec_out_voltage,
    detect=DETECT_SOCOMEC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.4.4.1",
        oids=["1", "2"],
    ),
    service_name="OUT voltage phase %s",
    discovery_function=inventory_socomec_ups_out_voltage,
    check_function=check_socomec_ups_out_voltage,
    check_ruleset_name="evolt",
    check_default_parameters={
        "levels_lower": (210.0, 180.0),
    },
)
