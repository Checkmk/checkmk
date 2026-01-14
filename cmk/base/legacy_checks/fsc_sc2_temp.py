#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fsc import DETECT_FSC_SC2
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

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


def discover_fsc_sc2_temp(info):
    for line in info:
        if line[1] != "2":
            yield line[0], {}


def check_fsc_sc2_temp(item, params, info):
    temp_status = {
        "1": (3, "unknown"),
        "2": (0, "not-available"),
        "3": (0, "ok"),
        "4": (2, "sensor-failed"),
        "5": (2, "failed"),
        "6": (1, "temperature-warning-toohot"),
        "7": (2, "temperature-critical-toohot"),
        "8": (0, "temperature-normal"),
        "9": (1, "temperature-warning"),
    }

    for designation, status, temp, dev_warn, dev_crit in info:
        if designation == item:
            if not temp:
                return 3, "Did not receive temperature data"

            dev_status, dev_status_name = temp_status.get(status, (3, "unknown"))

            if not dev_warn or not dev_crit:
                return 3, "Did not receive device levels"

            dev_levels = int(dev_warn), int(dev_crit)

            return check_temperature(
                int(temp),
                params,
                "temp_{}".format(item.replace(" ", "_")),
                "c",
                dev_levels,
                None,
                dev_status,
                dev_status_name,
            )
    return None


check_info["fsc_sc2_temp"] = LegacyCheckDefinition(
    name="fsc_sc2_temp",
    parse_function=parse_fsc_sc2_temp,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.5.1.1",
        oids=["3", "5", "6", "7", "8"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_fsc_sc2_temp,
    check_function=check_fsc_sc2_temp,
    check_ruleset_name="temperature",
)
