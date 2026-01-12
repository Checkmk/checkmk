#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.apc.lib_ats import DETECT
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# .1.3.6.1.4.1.318.1.1.13.3.2.2.2.7.0 197 --> PowerNet-MIB::airIRRCUnitStatusRackInletTempMetric.0
# .1.3.6.1.4.1.318.1.1.13.3.2.2.2.9.0 202 --> PowerNet-MIB::airIRRCUnitStatusSupplyAirTempMetric.0
# .1.3.6.1.4.1.318.1.1.13.3.2.2.2.11.0 219 --> PowerNet-MIB::airIRRCUnitStatusReturnAirTempMetric.0
# .1.3.6.1.4.1.318.1.1.13.3.2.2.2.24.0 131 --> PowerNet-MIB::airIRRCUnitStatusEnteringFluidTemperatureMetric.0
# .1.3.6.1.4.1.318.1.1.13.3.2.2.2.26.0 154 --> PowerNet-MIB::airIRRCUnitStatusLeavingFluidTemperatureMetric.0


def parse_apc_inrow_temp(string_table: StringTable) -> Mapping[str, float]:
    parsed = {}
    if string_table:
        for what, what_item in zip(
            string_table[0],
            ["Rack Inlet", "Supply Air", "Return Air", "Entering Fluid", "Leaving Fluid"],
            strict=False,
        ):
            if what not in ["", "-1"]:
                parsed[what_item] = float(what) / 10

    return parsed


def discover_apc_inrow_temp(section: Mapping[str, float]) -> DiscoveryResult:
    yield from (Service(item=key) for key in section)


def check_apc_inrow_temp(
    item: str, params: TempParamType, section: Mapping[str, float]
) -> CheckResult:
    if (temperature := section.get(item)) is not None:
        yield from check_temperature(
            temperature,
            params,
            unique_name=f"apc_inrow_temp_{item}",
            value_store=get_value_store(),
        )


snmp_section_apc_inrow_temp = SimpleSNMPSection(
    name="apc_inrow_temp",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.13.3.2.2.2",
        oids=["7", "9", "11", "24", "26"],
    ),
    parse_function=parse_apc_inrow_temp,
)


check_plugin_apc_inrow_temp = CheckPlugin(
    name="apc_inrow_temp",
    service_name="Temperature %s",
    discovery_function=discover_apc_inrow_temp,
    check_function=check_apc_inrow_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (30.0, 35.0)},
)
