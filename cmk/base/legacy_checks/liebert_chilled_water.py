#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.liebert import (
    DETECT_LIEBERT,
    parse_liebert_str_without_unit,
)

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.100.4626 Supply Chilled Water Over Temp
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.100.4626 Inactive Event
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.100.4703 Chilled Water Control Valve Failure
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.100.4703 Inactive Event
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.100.4980 Supply Chilled Water Loss of Flow
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.100.4980 Inactive Event


def inventory_liebert_chilled_water(parsed):
    for key in parsed:
        if key:
            yield (key, {})


def check_liebert_chilled_water(item, _params, parsed):
    for key, value in parsed.items():
        if item == key and value.lower() == "inactive event":
            yield 0, "Normal"
        elif item == key:
            yield 2, "%s" % value


check_info["liebert_chilled_water"] = LegacyCheckDefinition(
    detect=DETECT_LIEBERT,
    parse_function=parse_liebert_str_without_unit,
    discovery_function=inventory_liebert_chilled_water,
    check_function=check_liebert_chilled_water,
    service_name="%s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=[
            "10.1.2.100.4626",
            "20.1.2.100.4626",
            "10.1.2.100.4703",
            "20.1.2.100.4703",
            "10.1.2.100.4980",
            "20.1.2.100.4980",
        ],
    ),
)
