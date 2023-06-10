#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.liebert import check_temp_unit
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.liebert import DETECT_LIEBERT, parse_liebert_float

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5282 Actual Supply Fluid Temp Set Point
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5282 17.7
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5282 deg C
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5288 Return Fluid Temperature
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5288 4.3
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5288 deg C
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.4643 Supply Fluid Temperature
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.4643 11.1
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.4643 deg C
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5517 Condenser Inlet Water Temperature
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5517 Unavailable
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5517 deg C
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5518 Condenser Outlet Water Temperature
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5518 Unavailable
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5518 deg C


def check_liebert_temp_general(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    value = check_temp_unit(data)
    yield check_temperature(value, params, "check_liebert_fluid_temp.%s" % item)


def discover_liebert_temp_general(section):
    yield from ((item, {}) for item in section)


check_info["liebert_temp_general"] = LegacyCheckDefinition(
    detect=DETECT_LIEBERT,
    parse_function=parse_liebert_float,
    discovery_function=discover_liebert_temp_general,
    check_function=check_liebert_temp_general,
    service_name="%s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=[
            "10.1.2.2.5282",
            "20.1.2.2.5282",
            "30.1.2.2.5282",
            "10.1.2.2.5288",
            "20.1.2.2.5288",
            "30.1.2.2.5288",
            "10.1.2.2.4643",
            "20.1.2.2.4643",
            "30.1.2.2.4643",
            "10.1.2.2.5517",
            "20.1.2.2.5517",
            "30.1.2.2.5517",
            "10.1.2.2.5518",
            "20.1.2.2.5518",
            "30.1.2.2.5518",
            "10.1.2.1.5519",
            "20.1.2.1.5519",
            "30.1.2.1.5519",
        ],
    ),
    check_ruleset_name="temperature",
)
