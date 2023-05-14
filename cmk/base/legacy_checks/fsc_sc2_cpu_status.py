#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.fsc import DETECT_FSC_SC2
from cmk.base.check_legacy_includes.fsc_sc2 import (
    check_fsc_sc2_cpu_status,
    inventory_fsc_sc2_cpu_status,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

check_info["fsc_sc2_cpu_status"] = LegacyCheckDefinition(
    detect=DETECT_FSC_SC2,
    discovery_function=inventory_fsc_sc2_cpu_status,
    check_function=check_fsc_sc2_cpu_status,
    service_name="FSC %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.4.1",
        oids=["3", "4", "5", "8", "13"],
    ),
)
