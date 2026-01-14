#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.plugins.lib import ucd_hr_detection

check_info = {}

# .1.3.6.1.2.1.25.3.3.1.2.768 1 --> HOST-RESOURCES-MIB::hrProcessorLoad.768
# .1.3.6.1.2.1.25.3.3.1.2.769 1 --> HOST-RESOURCES-MIB::hrProcessorLoad.769


def discover_hr_cpu(info):
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


# Migration NOTE: Create a separate section, but a common check plug-in for
# tplink_cpu, hr_cpu, cisco_nexus_cpu, bintec_cpu, winperf_processor,
# lxc_container_cpu, docker_container_cpu.
# Migration via cmk/update_config.py!
def parse_hr_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["hr_cpu"] = LegacyCheckDefinition(
    name="hr_cpu",
    parse_function=parse_hr_cpu,
    detect=ucd_hr_detection.HR,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.25.3.3.1",
        oids=["2"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_hr_cpu,
    check_function=check_hr_cpu,
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={
        "util": (80.0, 90.0),
    },
)
