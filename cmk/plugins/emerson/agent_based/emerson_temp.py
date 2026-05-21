#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

#
# during inventory we are looking for all temperatures available,
# in this example there are two (index 1 & 2):
#
# EES-POWER-MIB::psTemperature1.0 .1.3.6.1.4.1.6302.2.1.2.7.1
# EES-POWER-MIB::psTemperature2.0 .1.3.6.1.4.1.6302.2.1.2.7.2
#
# the mib is the NetSure_ESNA.mib, which we have received from directly
# from a customer, its named "Emerson Energy Systems (EES) Power MIB"


def discover_emerson_temp(section: StringTable) -> DiscoveryResult:
    # Device appears to mark missing sensors by temperature value -999999
    yield from (Service(item=str(nr)) for nr, line in enumerate(section) if int(line[0]) >= -273000)


def check_emerson_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    item_index = int(item)
    if item_index >= len(section):
        return

    if int(section[item_index][0]) < -273000:
        yield Result(state=State.UNKNOWN, summary="Sensor offline")
        return

    temp = float(section[item_index][0]) / 1000.0
    yield from check_temperature(
        temp,
        params,
        unique_name=f"emerson_temp_{item}",
        value_store=get_value_store(),
    )


def parse_emerson_temp(string_table: StringTable) -> StringTable:
    # Only use the first two sensor values, as values beyond that seem to be handled in a different
    # structure that we lack a concrete definition for.
    return string_table[:2]


snmp_section_emerson_temp = SimpleSNMPSection(
    name="emerson_temp",
    detect=startswith(".1.3.6.1.4.1.6302.2.1.1.1.0", "Emerson Network Power"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6302.2.1.2",
        oids=["7"],
    ),
    parse_function=parse_emerson_temp,
)


check_plugin_emerson_temp = CheckPlugin(
    name="emerson_temp",
    service_name="Temperature %s",
    discovery_function=discover_emerson_temp,
    check_function=check_emerson_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (40.0, 50.0)},
)
