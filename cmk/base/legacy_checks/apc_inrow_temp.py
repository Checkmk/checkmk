#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.apc import DETECT

# .1.3.6.1.4.1.318.1.1.13.3.2.2.2.7.0 197 --> PowerNet-MIB::airIRRCUnitStatusRackInletTempMetric.0
# .1.3.6.1.4.1.318.1.1.13.3.2.2.2.9.0 202 --> PowerNet-MIB::airIRRCUnitStatusSupplyAirTempMetric.0
# .1.3.6.1.4.1.318.1.1.13.3.2.2.2.11.0 219 --> PowerNet-MIB::airIRRCUnitStatusReturnAirTempMetric.0
# .1.3.6.1.4.1.318.1.1.13.3.2.2.2.24.0 131 --> PowerNet-MIB::airIRRCUnitStatusEnteringFluidTemperatureMetric.0
# .1.3.6.1.4.1.318.1.1.13.3.2.2.2.26.0 154 --> PowerNet-MIB::airIRRCUnitStatusLeavingFluidTemperatureMetric.0


def parse_apc_inrow_temp(info):
    parsed = {}
    if info:
        for what, what_item in zip(
            info[0], ["Rack Inlet", "Supply Air", "Return Air", "Entering Fluid", "Leaving Fluid"]
        ):
            if what not in ["", "-1"]:
                parsed.setdefault(what_item, float(what) / 10)

    return parsed


def inventory_apc_inrow_temp(parsed):
    for key in parsed:
        yield key, {}


def check_apc_inrow_temp(item, params, parsed):
    if item in parsed:
        return check_temperature(parsed[item], params, "apc_inrow_temp_%s" % item)
    return None


check_info["apc_inrow_temp"] = LegacyCheckDefinition(
    detect=DETECT,
    parse_function=parse_apc_inrow_temp,
    discovery_function=inventory_apc_inrow_temp,
    check_function=check_apc_inrow_temp,
    service_name="Temperature %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.13.3.2.2.2",
        oids=["7", "9", "11", "24", "26"],
    ),
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (30.0, 35.0)},
)
