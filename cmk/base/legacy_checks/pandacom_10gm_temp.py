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
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.pandacom import DETECT_PANDACOM

# .1.3.6.1.4.1.3652.3.3.4.1.1.2.4 4 --> SPEED-DUALLINE-10G::speedDualline10GMSlot.4
# .1.3.6.1.4.1.3652.3.3.4.1.1.2.5 5 --> SPEED-DUALLINE-10G::speedDualline10GMSlot.5
# .1.3.6.1.4.1.3652.3.3.4.1.1.7.4 30 --> SPEED-DUALLINE-10G::speedDualline10GMTemperature.4
# .1.3.6.1.4.1.3652.3.3.4.1.1.7.5 32 --> SPEED-DUALLINE-10G::speedDualline10GMTemperature.5
# .1.3.6.1.4.1.3652.3.3.4.2.1.13.4 45 --> SPEED-DUALLINE-10G::speedDualline10GMTempWarningLevel.4
# .1.3.6.1.4.1.3652.3.3.4.2.1.13.5 45 --> SPEED-DUALLINE-10G::speedDualline10GMTempWarningLevel.5
# .1.3.6.1.4.1.3652.3.3.4.2.1.14.4 60 --> SPEED-DUALLINE-10G::speedDualline10GMTempAlarmLevel.4
# .1.3.6.1.4.1.3652.3.3.4.2.1.14.5 60 --> SPEED-DUALLINE-10G::speedDualline10GMTempAlarmLevel.5


check_info["pandacom_10gm_temp"] = LegacyCheckDefinition(
    detect=DETECT_PANDACOM,
    discovery_function=inventory_pandacom_module_temp,
    check_function=check_pandacom_module_temp,
    service_name="Temperature 10GM Module %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3652.3.3.4",
        oids=["1.1.2", "1.1.7", "2.1.13", "2.1.14"],
    ),
    check_ruleset_name="temperature",
    check_default_parameters=PANDACOM_TEMP_CHECK_DEFAULT_PARAMETERS,
)
