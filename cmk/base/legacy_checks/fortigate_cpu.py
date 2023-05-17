#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import all_of, contains, exists, LegacyCheckDefinition, not_exists
from cmk.base.check_legacy_includes.fortigate_cpu import (
    check_fortigate_cpu,
    inventory_fortigate_cpu,
)
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

factory_settings["fortigate_cpu_default_levels"] = {"util": (80.0, 90.0)}


check_info["fortigate_cpu"] = LegacyCheckDefinition(
    detect=all_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1"),
        exists(".1.3.6.1.4.1.12356.1.8.0"),
        not_exists(".1.3.6.1.4.1.12356.101.4.1.3.0"),
    ),
    discovery_function=inventory_fortigate_cpu,
    check_function=check_fortigate_cpu,
    service_name="CPU utilization",
    check_ruleset_name="cpu_utilization",
    # uses mib FORTINET-MIB-280
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.1",
        oids=["8"],
    ),
    default_levels_variable="fortigate_cpu_default_levels",
    check_default_parameters={"util": (80.0, 90.0)},
)
