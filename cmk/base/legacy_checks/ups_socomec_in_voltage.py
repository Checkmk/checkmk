#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.check_legacy_includes.ups_in_voltage import check_ups_in_voltage
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.ups_socomec import DETECT_SOCOMEC


def inventory_socomec_ups_in_voltage(info):
    yield from ((x[0], {}) for x in info if int(x[1]) > 0)


def check_socomec_ups_in_voltage(item, params, info):
    conv_info = []
    for line in info:
        conv_info.append([line[0], saveint(line[1]) // 10, line[1]])
    return check_ups_in_voltage(item, params, conv_info)


check_info["ups_socomec_in_voltage"] = LegacyCheckDefinition(
    detect=DETECT_SOCOMEC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.3.3.1",
        oids=["1", "2"],
    ),
    service_name="IN voltage phase %s",
    discovery_function=inventory_socomec_ups_in_voltage,
    check_function=check_socomec_ups_in_voltage,
    check_ruleset_name="evolt",
    check_default_parameters={
        "levels_lower": (210.0, 180.0),
    },
)
