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
    State,
    StringTable,
)
from cmk.plugins.fujitsu.lib import DETECT_FSC_SC2
from cmk.plugins.lib.temperature import check_temperature, TempParamType

_TEMP_STATUS = {
    "1": (State.UNKNOWN, "unknown"),
    "2": (State.OK, "not-available"),
    "3": (State.OK, "ok"),
    "4": (State.CRIT, "sensor-failed"),
    "5": (State.CRIT, "failed"),
    "6": (State.WARN, "temperature-warning-toohot"),
    "7": (State.CRIT, "temperature-critical-toohot"),
    "8": (State.OK, "temperature-normal"),
    "9": (State.WARN, "temperature-warning"),
}

# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.1.1 "Ambient"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.1.2 "Systemboard 1"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.1.3 "Systemboard 2"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.1.4 "CPU1"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.1.5 "CPU2"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.1.6 "MEM A"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.1.7 "MEM B"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.1.8 "MEM C"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.1.9 "MEM D"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.5.1.1 8
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.5.1.2 8
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.5.1.3 8
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.5.1.4 8
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.5.1.5 2
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.5.1.6 8
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.5.1.7 8
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.5.1.8 8
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.5.1.9 8
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.6.1.1 26
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.6.1.2 27
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.6.1.3 33
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.6.1.4 27
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.6.1.5 0
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.6.1.6 28
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.6.1.7 28
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.6.1.8 27
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.6.1.9 27
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.7.1.1 37
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.7.1.2 75
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.7.1.3 75
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.7.1.4 77
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.7.1.5 89
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.7.1.6 78
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.7.1.7 78
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.7.1.8 78
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.7.1.9 78
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.8.1.1 42
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.8.1.2 80
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.8.1.3 80
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.8.1.4 81
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.8.1.5 93
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.8.1.6 82
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.8.1.7 82
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.8.1.8 82
# .1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.8.1.9 82


def parse_fsc_sc2_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_fsc_sc2_temp(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1] != "2":
            yield Service(item=line[0])


def check_fsc_sc2_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for designation, status, temp, dev_warn, dev_crit in section:
        if designation == item:
            if not temp:
                yield Result(state=State.UNKNOWN, summary="Did not receive temperature data")
                return

            dev_status, dev_status_name = _TEMP_STATUS.get(status, (State.UNKNOWN, "unknown"))

            if not dev_warn or not dev_crit:
                yield Result(state=State.UNKNOWN, summary="Did not receive device levels")
                return

            yield from check_temperature(
                int(temp),
                params,
                unique_name="temp_{}".format(item.replace(" ", "_")),
                value_store=get_value_store(),
                dev_levels=(int(dev_warn), int(dev_crit)),
                dev_status=int(dev_status),
                dev_status_name=dev_status_name,
            )
            return


snmp_section_fsc_sc2_temp = SimpleSNMPSection(
    name="fsc_sc2_temp",
    parse_function=parse_fsc_sc2_temp,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.5.1.1",
        oids=["3", "5", "6", "7", "8"],
    ),
)


check_plugin_fsc_sc2_temp = CheckPlugin(
    name="fsc_sc2_temp",
    service_name="Temperature %s",
    discovery_function=discover_fsc_sc2_temp,
    check_function=check_fsc_sc2_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
