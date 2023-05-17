#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.pandacom_temp import (
    check_pandacom_module_temp,
    inventory_pandacom_module_temp,
    PANDACOM_TEMP_CHECK_DEFAULT_PARAMETERS,
)
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.pandacom import DETECT_PANDACOM

# .1.3.6.1.4.1.3652.3.3.3.1.1.2.2 2 --> SPEED-DUALLINE-FC::speedDuallineFCMSlot.2
# .1.3.6.1.4.1.3652.3.3.3.1.1.2.3 3 --> SPEED-DUALLINE-FC::speedDuallineFCMSlot.3
# .1.3.6.1.4.1.3652.3.3.3.1.1.7.2 31  --> SPEED-DUALLINE-FC::speedDuallineFCMTemperature.2
# .1.3.6.1.4.1.3652.3.3.3.1.1.7.3 29  --> SPEED-DUALLINE-FC::speedDuallineFCMTemperature.3
# .1.3.6.1.4.1.3652.3.3.3.2.1.13.2 45 --> SPEED-DUALLINE-FC::speedDuallineFCMTempWarningLevel.2
# .1.3.6.1.4.1.3652.3.3.3.2.1.13.3 45 --> SPEED-DUALLINE-FC::speedDuallineFCMTempWarningLevel.3
# .1.3.6.1.4.1.3652.3.3.3.2.1.14.2 60 --> SPEED-DUALLINE-FC::speedDuallineFCMTempAlarmLevel.2
# .1.3.6.1.4.1.3652.3.3.3.2.1.14.3 60 --> SPEED-DUALLINE-FC::speedDuallineFCMTempAlarmLevel.3


factory_settings["pandacom_temp_default_levels"] = PANDACOM_TEMP_CHECK_DEFAULT_PARAMETERS

check_info["pandacom_fc_temp"] = LegacyCheckDefinition(
    detect=DETECT_PANDACOM,
    discovery_function=inventory_pandacom_module_temp,
    check_function=check_pandacom_module_temp,
    service_name="Temperature FC Module %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3652.3.3.3",
        oids=["1.1.2", "1.1.7", "2.1.13", "2.1.14"],
    ),
    default_levels_variable="pandacom_temp_default_levels",
    check_ruleset_name="temperature",
    check_default_parameters=PANDACOM_TEMP_CHECK_DEFAULT_PARAMETERS,
)
