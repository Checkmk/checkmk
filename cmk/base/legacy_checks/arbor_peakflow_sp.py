#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.arbor import (
    check_arbor_disk_usage,
    inventory_arbor_disk_usage,
)
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.arbor import DETECT_PEAKFLOW_SP
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

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


def parse_peakflow_sp(string_table):
    if not string_table:
        return None
    valid = string_table[0]
    res = {"disk": valid[0]}
    if valid[1]:
        # this value appears to be optional
        res["flows"] = valid[1]

    return res


check_info["arbor_peakflow_sp"] = LegacyCheckDefinition(
    detect=DETECT_PEAKFLOW_SP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.4.2.1",
        oids=["4.0", "12.0"],
    ),
    parse_function=parse_peakflow_sp,
)

check_info["arbor_peakflow_sp.disk_usage"] = LegacyCheckDefinition(
    service_name="Disk Usage %s",
    sections=["arbor_peakflow_sp"],
    discovery_function=inventory_arbor_disk_usage,
    check_function=check_arbor_disk_usage,
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
    service_name="Flow Count",
    sections=["arbor_peakflow_sp"],
    discovery_function=inventory_arbor_peakflow_sp_flows,
    check_function=check_arbor_peakflow_sp_flows,
)
