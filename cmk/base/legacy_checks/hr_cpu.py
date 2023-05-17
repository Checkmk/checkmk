#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils import ucd_hr_detection

# .1.3.6.1.2.1.25.3.3.1.2.768 1 --> HOST-RESOURCES-MIB::hrProcessorLoad.768
# .1.3.6.1.2.1.25.3.3.1.2.769 1 --> HOST-RESOURCES-MIB::hrProcessorLoad.769

factory_settings["hr_cpu_default_levels"] = {
    "util": (80.0, 90.0),
}


def inventory_hr_cpu(info):
    if len(info) >= 1:
        return [(None, {})]
    return []


def check_hr_cpu(_no_item, params, info):
    num_cpus = 0
    util = 0.0
    cores = []
    for line in info:
        core_util = int(line[0])
        cores.append(("core%d" % num_cpus, core_util))
        util += core_util
        num_cpus += 1
    if num_cpus == 0:
        return 3, "No data found in SNMP output"
    util = float(util) / num_cpus
    return check_cpu_util(util, params, cores=cores)


# Migration NOTE: Create a separate section, but a common check plugin for
# tplink_cpu, hr_cpu, cisco_nexus_cpu, bintec_cpu, winperf_processor,
# lxc_container_cpu, docker_container_cpu.
# Migration via cmk/update_config.py!
check_info["hr_cpu"] = LegacyCheckDefinition(
    detect=ucd_hr_detection.HR,
    discovery_function=inventory_hr_cpu,
    check_function=check_hr_cpu,
    service_name="CPU utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.25.3.3.1",
        oids=["2"],
    ),
    check_ruleset_name="cpu_utilization_os",
    default_levels_variable="hr_cpu_default_levels",
    check_default_parameters={
        "util": (80.0, 90.0),
    },
)
