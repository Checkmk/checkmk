#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import MutableMapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict
from cmk.plugins.liebert.agent_based.lib import (
    DETECT_LIEBERT,
    parse_liebert_float,
    Section,
    temperature_to_celsius,
)

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


def check_liebert_temp_general(
    item: str, params: TempParamDict, section: Section[float]
) -> CheckResult:
    yield from check_liebert_temp_general_testable(item, params, section, get_value_store())


def check_liebert_temp_general_testable(
    item: str,
    params: TempParamDict,
    section: Section[float],
    value_store: MutableMapping[str, object],
) -> CheckResult:
    try:
        value, unit = section[item]
    except KeyError:
        return
    yield from check_temperature(
        temperature_to_celsius(value, unit),
        params,
        unique_name="check_liebert_fluid_temp.%s" % item,
        value_store=value_store,
    )


def discover_liebert_temp_general(section: Section[float]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_liebert_temp_general = SimpleSNMPSection(
    name="liebert_temp_general",
    detect=DETECT_LIEBERT,
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
    parse_function=parse_liebert_float,
)
check_plugin_liebert_temp_general = CheckPlugin(
    name="liebert_temp_general",
    service_name="%s",
    discovery_function=discover_liebert_temp_general,
    check_function=check_liebert_temp_general,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
