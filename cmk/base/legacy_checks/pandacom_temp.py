#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.pandacom import DETECT_PANDACOM

check_info = {}

PANDACOM_TEMP_CHECK_DEFAULT_PARAMETERS = {"levels": (35.0, 40.0)}


def parse_pandacom_temp(string_table: StringTable) -> StringTable:
    return string_table


def inventory_pandacom_module_temp(info):
    return [(line[0], {}) for line in info]


def check_pandacom_module_temp(item, params, info):
    for slot, temp_str, warn_str, crit_str in info:
        if slot == item:
            return check_temperature(
                int(temp_str),
                params,
                "pandacom_%s" % item,
                dev_levels=(int(warn_str), int(crit_str)),
            )
    return None


check_info["pandacom_10gm_temp"] = LegacyCheckDefinition(
    name="pandacom_10gm_temp",
    parse_function=parse_pandacom_temp,
    detect=DETECT_PANDACOM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3652.3.3.4",
        # .1.3.6.1.4.1.3652.3.3.4.1.1.2.4 4 --> SPEED-DUALLINE-10G::speedDualline10GMSlot.4
        # .1.3.6.1.4.1.3652.3.3.4.1.1.2.5 5 --> SPEED-DUALLINE-10G::speedDualline10GMSlot.5
        # .1.3.6.1.4.1.3652.3.3.4.1.1.7.4 30 --> SPEED-DUALLINE-10G::speedDualline10GMTemperature.4
        # .1.3.6.1.4.1.3652.3.3.4.1.1.7.5 32 --> SPEED-DUALLINE-10G::speedDualline10GMTemperature.5
        # .1.3.6.1.4.1.3652.3.3.4.2.1.13.4 45 --> SPEED-DUALLINE-10G::speedDualline10GMTempWarningLevel.4
        # .1.3.6.1.4.1.3652.3.3.4.2.1.13.5 45 --> SPEED-DUALLINE-10G::speedDualline10GMTempWarningLevel.5
        # .1.3.6.1.4.1.3652.3.3.4.2.1.14.4 60 --> SPEED-DUALLINE-10G::speedDualline10GMTempAlarmLevel.4
        # .1.3.6.1.4.1.3652.3.3.4.2.1.14.5 60 --> SPEED-DUALLINE-10G::speedDualline10GMTempAlarmLevel.5
        oids=["1.1.2", "1.1.7", "2.1.13", "2.1.14"],
    ),
    service_name="Temperature 10GM Module %s",
    discovery_function=inventory_pandacom_module_temp,
    check_function=check_pandacom_module_temp,
    check_ruleset_name="temperature",
    check_default_parameters=PANDACOM_TEMP_CHECK_DEFAULT_PARAMETERS,
)


check_info["pandacom_fc_temp"] = LegacyCheckDefinition(
    name="pandacom_fc_temp",
    parse_function=parse_pandacom_temp,
    detect=DETECT_PANDACOM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3652.3.3.3",
        # .1.3.6.1.4.1.3652.3.3.3.1.1.2.2 2 --> SPEED-DUALLINE-FC::speedDuallineFCMSlot.2
        # .1.3.6.1.4.1.3652.3.3.3.1.1.2.3 3 --> SPEED-DUALLINE-FC::speedDuallineFCMSlot.3
        # .1.3.6.1.4.1.3652.3.3.3.1.1.7.2 31  --> SPEED-DUALLINE-FC::speedDuallineFCMTemperature.2
        # .1.3.6.1.4.1.3652.3.3.3.1.1.7.3 29  --> SPEED-DUALLINE-FC::speedDuallineFCMTemperature.3
        # .1.3.6.1.4.1.3652.3.3.3.2.1.13.2 45 --> SPEED-DUALLINE-FC::speedDuallineFCMTempWarningLevel.2
        # .1.3.6.1.4.1.3652.3.3.3.2.1.13.3 45 --> SPEED-DUALLINE-FC::speedDuallineFCMTempWarningLevel.3
        # .1.3.6.1.4.1.3652.3.3.3.2.1.14.2 60 --> SPEED-DUALLINE-FC::speedDuallineFCMTempAlarmLevel.2
        # .1.3.6.1.4.1.3652.3.3.3.2.1.14.3 60 --> SPEED-DUALLINE-FC::speedDuallineFCMTempAlarmLevel.3
        oids=["1.1.2", "1.1.7", "2.1.13", "2.1.14"],
    ),
    service_name="Temperature FC Module %s",
    discovery_function=inventory_pandacom_module_temp,
    check_function=check_pandacom_module_temp,
    check_ruleset_name="temperature",
    check_default_parameters=PANDACOM_TEMP_CHECK_DEFAULT_PARAMETERS,
)
