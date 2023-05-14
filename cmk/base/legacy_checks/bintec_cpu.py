#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, startswith
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

# Diese OIDs liefern nicht die LOAD, wie man annehmen könnte, sondern die
# UTILIZATION, da ausschließlich die Auslastung der CPU berücksichtigt wird.
# .1.3.6.1.4.1.272.4.17.4.1.1.15.1.0 5 --> BIANCA-BRICK-MIBRES-MIB::CpuLoadUser60s.1.0
# .1.3.6.1.4.1.272.4.17.4.1.1.16.1.0 1 --> BIANCA-BRICK-MIBRES-MIB::CpuLoadSystem60s.1.0
# .1.3.6.1.4.1.272.4.17.4.1.1.17.1.0 9 --> BIANCA-BRICK-MIBRES-MIB::CpuLoadStreams60s.1.0


def inventory_bintec_cpu(info):
    if info:
        return [(None, {})]
    return []


def check_bintec_cpu(_no_item, params, info):
    user = float(info[0][0])
    system = float(info[0][1])
    streams = float(info[0][2])
    util = user + system + streams

    yield 0, "user: %.1f%%" % user
    yield 0, "system: %.1f%%" % system
    yield 0, "streams: %.1f%%" % streams, [("streams", streams)]

    for res in check_cpu_util(util, params):
        yield res


# Migration NOTE: Create a separate section, but a common check plugin for
# tplink_cpu, hr_cpu, cisco_nexus_cpu, bintec_cpu, winperf_processor,
# lxc_container_cpu, docker_container_cpu.
# Migration via cmk/update_config.py!
check_info["bintec_cpu"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.272.4."),
    discovery_function=inventory_bintec_cpu,
    check_function=check_bintec_cpu,
    service_name="CPU utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.272.4.17.4.1.1",
        oids=["15", "16", "17"],
    ),
    check_ruleset_name="cpu_utilization_os",
)
