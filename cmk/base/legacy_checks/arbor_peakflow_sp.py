#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.arbor import (
    ARBOR_MEMORY_CHECK_DEFAULT_PARAMETERS,
    check_arbor_disk_usage,
    check_arbor_memory,
    inventory_arbor_disk_usage,
    inventory_arbor_memory,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_PARAMS

# .1.3.6.1.4.1.9694.1.4.2.1.1.0 796 --> PEAKFLOW-SP-MIB::deviceCpuLoadAvg1min.0
# .1.3.6.1.4.1.9694.1.4.2.1.2.0 742 --> PEAKFLOW-SP-MIB::deviceCpuLoadAvg5min.0
# .1.3.6.1.4.1.9694.1.4.2.1.3.0 742 --> PEAKFLOW-SP-MIB::deviceCpuLoadAvg15min.0
# .1.3.6.1.4.1.9694.1.4.2.1.4.0 0 --> PEAKFLOW-SP-MIB::deviceDiskUsage.0
# .1.3.6.1.4.1.9694.1.4.2.1.5.0 32864948 --> PEAKFLOW-SP-MIB::devicePhysicalMemory.0
# .1.3.6.1.4.1.9694.1.4.2.1.6.0 4793660 --> PEAKFLOW-SP-MIB::devicePhysicalMemoryInUse.0
# .1.3.6.1.4.1.9694.1.4.2.1.7.0 15 --> PEAKFLOW-SP-MIB::devicePhysicalMemoryUsage.0
# .1.3.6.1.4.1.9694.1.4.2.1.8.0 4892156 --> PEAKFLOW-SP-MIB::deviceSwapSpace.0
# .1.3.6.1.4.1.9694.1.4.2.1.9.0 0 --> PEAKFLOW-SP-MIB::deviceSwapSpaceInUse.0
# .1.3.6.1.4.1.9694.1.4.2.1.10.0 0 --> PEAKFLOW-SP-MIB::deviceSwapSpaceUsage.0
# .1.3.6.1.4.1.9694.1.4.2.1.11.0 0 --> PEAKFLOW-SP-MIB::deviceTotalFlows.0
# .1.3.6.1.4.1.9694.1.4.2.1.12.0 0 --> PEAKFLOW-SP-MIB::deviceTotalFlowsHC.0


def parse_peakflow_sp(info):
    valid = info[0]
    res = {"disk": valid[0], "memory": valid[1:3]}
    if valid[3]:
        # this value appears to be optional
        res["flows"] = valid[3]

    return res


check_info["arbor_peakflow_sp"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.1.0", "Peakflow SP"),
    check_function=check_arbor_memory,
    discovery_function=inventory_arbor_memory,
    parse_function=parse_peakflow_sp,
    service_name="Memory",
    check_ruleset_name="memory_arbor",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.4.2.1",
        oids=["4.0", "7.0", "10.0", "12.0"],
    ),
    check_default_parameters=ARBOR_MEMORY_CHECK_DEFAULT_PARAMETERS,
)

check_info["arbor_peakflow_sp.disk_usage"] = LegacyCheckDefinition(
    check_function=check_arbor_disk_usage,
    discovery_function=inventory_arbor_disk_usage,
    service_name="Disk Usage %s",
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)


def inventory_arbor_peakflow_sp_flows(parsed):
    if "flows" in parsed:
        return [(None, None)]
    return []


def check_arbor_peakflow_sp_flows(_no_item, params, parsed):
    flows = int(parsed["flows"])
    return 0, "%d flows" % flows, [("flows", flows)]


check_info["arbor_peakflow_sp.flows"] = LegacyCheckDefinition(
    check_function=check_arbor_peakflow_sp_flows,
    discovery_function=inventory_arbor_peakflow_sp_flows,
    service_name="Flow Count",
)
