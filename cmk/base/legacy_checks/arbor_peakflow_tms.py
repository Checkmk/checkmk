#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.arbor import (
    check_arbor_disk_usage,
    check_arbor_host_fault,
    inventory_arbor_disk_usage,
    inventory_arbor_host_fault,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.arbor import DETECT_PEAKFLOW_TMS
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

# .1.3.6.1.4.1.9694.1.5.2.1.0 No Fault --> PEAKFLOW-TMS-MIB::tmsHostFault.0
# .1.3.6.1.4.1.9694.1.5.2.2.0 101420100 --> PEAKFLOW-TMS-MIB::tmsHostUpTime.0
# .1.3.6.1.4.1.9694.1.5.2.3.0 46 --> PEAKFLOW-TMS-MIB::deviceCpuLoadAvg1min.0
# .1.3.6.1.4.1.9694.1.5.2.4.0 64 --> PEAKFLOW-TMS-MIB::deviceCpuLoadAvg5min.0
# .1.3.6.1.4.1.9694.1.5.2.5.0 67 --> PEAKFLOW-TMS-MIB::deviceCpuLoadAvg15min.0
# .1.3.6.1.4.1.9694.1.5.2.6.0 6 --> PEAKFLOW-TMS-MIB::deviceDiskUsage.0
# .1.3.6.1.4.1.9694.1.5.2.7.0 4 --> PEAKFLOW-TMS-MIB::devicePhysicalMemoryUsage.0
# .1.3.6.1.4.1.9694.1.5.2.8.0 0 --> PEAKFLOW-TMS-MIB::deviceSwapSpaceUsage.0


def parse_peakflow_tms(string_table):
    health = string_table[0][0]
    updates = string_table[1][0]
    return {
        "disk": health[0],
        "host_fault": health[1],
        "update": {"Device": updates[0], "Mitigation": updates[1]},
    }


check_info["arbor_peakflow_tms"] = LegacyCheckDefinition(
    detect=DETECT_PEAKFLOW_TMS,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9694.1.5.2",
            oids=["6.0", "1.0"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9694.1.5.5",
            oids=["1.2.0", "2.1.0"],
        ),
    ],
    parse_function=parse_peakflow_tms,
)

check_info["arbor_peakflow_tms.disk_usage"] = LegacyCheckDefinition(
    service_name="Disk Usage %s",
    sections=["arbor_peakflow_tms"],
    discovery_function=inventory_arbor_disk_usage,
    check_function=check_arbor_disk_usage,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)

check_info["arbor_peakflow_tms.host_fault"] = LegacyCheckDefinition(
    service_name="Host Fault",
    sections=["arbor_peakflow_tms"],
    discovery_function=inventory_arbor_host_fault,
    check_function=check_arbor_host_fault,
)


def inventory_peakflow_tms_updates(parsed):
    for name in parsed["update"]:
        yield name, None


def check_peakflow_tms_updates(item, _no_params, parsed):
    if item in parsed["update"]:
        return 0, parsed["update"][item]
    return None


check_info["arbor_peakflow_tms.updates"] = LegacyCheckDefinition(
    service_name="Config Update %s",
    sections=["arbor_peakflow_tms"],
    discovery_function=inventory_peakflow_tms_updates,
    check_function=check_peakflow_tms_updates,
)
