#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.arbor import (
    ARBOR_MEMORY_CHECK_DEFAULT_PARAMETERS,
    check_arbor_disk_usage,
    check_arbor_drop_rate,
    check_arbor_host_fault,
    check_arbor_memory,
    inventory_arbor_disk_usage,
    inventory_arbor_drop_rate,
    inventory_arbor_host_fault,
    inventory_arbor_memory,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_PARAMS

# .1.3.6.1.4.1.9694.1.6.2.3.0 2070 --> PRAVAIL-MIB::deviceCpuLoadAvg1min.0
# .1.3.6.1.4.1.9694.1.6.2.4.0 2059 --> PRAVAIL-MIB::deviceCpuLoadAvg5min.0
# .1.3.6.1.4.1.9694.1.6.2.5.0 2059 --> PRAVAIL-MIB::deviceCpuLoadAvg15min.0
# .1.3.6.1.4.1.9694.1.6.2.6.0 8 --> PRAVAIL-MIB::deviceDiskUsage.0
# .1.3.6.1.4.1.9694.1.6.2.7.0 49 --> PRAVAIL-MIB::devicePhysicalMemoryUsage.0
# .1.3.6.1.4.1.9694.1.6.2.8.0 0 --> PRAVAIL-MIB::deviceSwapSpaceUsage.0
# .1.3.6.1.4.1.9694.1.6.2.39.0 43 --> PRAVAIL-MIB::pravailOverrunDropRatePps.0


def parse_pravail(info):
    # peakflow SP and TMS have the same info in different oid ranges
    valid = info[0]
    return {
        "disk": valid[0],
        "memory": valid[1:3],
        "host_fault": valid[3],
        "drop_rate": valid[4],
    }


check_info["arbor_pravail"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.1.0", "Pravail"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.6.2",
        oids=["6.0", "7.0", "8.0", "1.0", "39.0"],
    ),
    parse_function=parse_pravail,
    service_name="Memory",
    discovery_function=inventory_arbor_memory,
    check_function=check_arbor_memory,
    check_ruleset_name="memory_arbor",
    check_default_parameters=ARBOR_MEMORY_CHECK_DEFAULT_PARAMETERS,
)

check_info["arbor_pravail.disk_usage"] = LegacyCheckDefinition(
    service_name="Disk Usage %s",
    sections=["arbor_pravail"],
    discovery_function=inventory_arbor_disk_usage,
    check_function=check_arbor_disk_usage,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)

check_info["arbor_pravail.host_fault"] = LegacyCheckDefinition(
    service_name="Host Fault",
    sections=["arbor_pravail"],
    discovery_function=inventory_arbor_host_fault,
    check_function=check_arbor_host_fault,
)

check_info["arbor_pravail.drop_rate"] = LegacyCheckDefinition(
    service_name="%s drop rate",
    sections=["arbor_pravail"],
    discovery_function=inventory_arbor_drop_rate,
    check_function=check_arbor_drop_rate,
    check_ruleset_name="generic_rate",
)
