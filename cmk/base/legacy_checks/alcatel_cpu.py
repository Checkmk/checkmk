#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.alcatel import check_alcatel_cpu, inventory_alcatel_cpu
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.alcatel import DETECT_ALCATEL

check_info["alcatel_cpu"] = LegacyCheckDefinition(
    detect=DETECT_ALCATEL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.2.1.16.1.1.1",
        oids=["13"],
    ),
    service_name="CPU utilization",
    discovery_function=inventory_alcatel_cpu,
    check_function=check_alcatel_cpu,
)
