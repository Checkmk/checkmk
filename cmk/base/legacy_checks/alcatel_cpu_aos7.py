#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.alcatel import check_alcatel_cpu, inventory_alcatel_cpu
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.alcatel import DETECT_ALCATEL_AOS7

check_info["alcatel_cpu_aos7"] = LegacyCheckDefinition(
    detect=DETECT_ALCATEL_AOS7,
    check_function=check_alcatel_cpu,
    discovery_function=inventory_alcatel_cpu,
    service_name="CPU utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.801.1.2.1.16.1.1.1.1.1",
        oids=["15"],
    ),
)
