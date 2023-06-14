#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, SNMPTree

# [[[u'26', u'26']], [[u'45', u'15', u'45', u'15']]]


def inventory_cmc_temp(info):
    # There are always two sensors
    return [("1", {}), ("2", {})]


def check_cmc_temp(item, params, info):
    offset = int(item) - 1
    current_temp = int(info[0][0][offset])
    dev_high, dev_low = map(int, info[1][0][offset * 2 :][:2])
    return check_temperature(
        current_temp,
        params,
        "cmc_temp_%s" % item,
        dev_levels=(dev_high, dev_high),
        dev_levels_lower=(dev_low, dev_low),
    )


check_info["cmc_temp"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2606.1"),
    discovery_function=inventory_cmc_temp,
    check_function=check_cmc_temp,
    check_ruleset_name="temperature",
    service_name="Temperature Sensor %s",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2606.1.1",
            oids=["1", "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2606.1.4",
            oids=["4", "5", "6", "7"],
        ),
    ],
    check_default_parameters={
        "levels": (45.0, 50.0),
    },
)
