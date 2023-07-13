#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.perle import check_perle_cm_modules, inventory_perle_cm_modules
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.perle import DETECT_PERLE

check_info["perle_modules_cm1110"] = LegacyCheckDefinition(
    detect=DETECT_PERLE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1966.21.1.1.1.1.4.3",
        oids=[
            "1.1.3",
            "3.1.3",
            "1.1.2",
            "1.1.21",
            "1.1.15",
            "1.1.16",
            "1.1.18",
            "1.1.32",
            "1.1.25",
            "1.1.26",
            "1.1.28",
        ],
    ),
    service_name="Chassis slot %s CM1110",
    discovery_function=inventory_perle_cm_modules,
    check_function=check_perle_cm_modules,
)
