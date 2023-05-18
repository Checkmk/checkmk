#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import all_of, contains, exists, LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

# .1.3.6.1.4.1.9.9.305.1.1.1.0 1 --> CISCO-SYSTEM-EXT-MIB::cseSysCPUUtilization.0


def inventory_cisco_nexus_cpu(info):
    if info[0][0]:
        return [(None, {})]
    return []


def check_cisco_nexus_cpu(_no_item, params, info):
    return check_cpu_util(float(info[0][0]), params)


# Migration NOTE: Create a separate section, but a common check plugin for
# tplink_cpu, hr_cpu, cisco_nexus_cpu, bintec_cpu, winperf_processor,
# lxc_container_cpu, docker_container_cpu.
# Migration via cmk/update_config.py!
check_info["cisco_nexus_cpu"] = LegacyCheckDefinition(
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"),
        contains(".1.3.6.1.2.1.1.1.0", "nx-os"),
        exists(".1.3.6.1.4.1.9.9.305.1.1.1.0"),
    ),
    discovery_function=inventory_cisco_nexus_cpu,
    check_function=check_cisco_nexus_cpu,
    service_name="CPU utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.305.1.1.1",
        oids=["0"],
    ),
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={
        "util": (80.0, 90.0),
    },
)
