#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict
from cmk.plugins.pandacom.lib import DETECT_PANDACOM


def parse_pandacom_sys_temp(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_pandacom_sys_temp(section: StringTable) -> DiscoveryResult:
    yield Service(item="System")


def check_pandacom_sys_temp(item: str, params: TempParamDict, section: StringTable) -> CheckResult:
    yield from check_temperature(int(section[0][0]), params)


snmp_section_pandacom_sys_temp = SimpleSNMPSection(
    name="pandacom_sys_temp",
    detect=DETECT_PANDACOM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3652.3.1.1",
        oids=["6"],
    ),
    parse_function=parse_pandacom_sys_temp,
)


check_plugin_pandacom_sys_temp = CheckPlugin(
    name="pandacom_sys_temp",
    service_name="Temperature %s",
    discovery_function=discover_pandacom_sys_temp,
    check_function=check_pandacom_sys_temp,
    check_ruleset_name="temperature",
    check_default_parameters=TempParamDict(levels=(35.0, 40.0)),
)
