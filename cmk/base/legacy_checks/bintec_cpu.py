#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}

# Diese OIDs liefern nicht die LOAD, wie man annehmen könnte, sondern die
# UTILIZATION, da ausschließlich die Auslastung der CPU berücksichtigt wird.
# .1.3.6.1.4.1.272.4.17.4.1.1.15.1.0 5 --> BIANCA-BRICK-MIBRES-MIB::CpuLoadUser60s.1.0
# .1.3.6.1.4.1.272.4.17.4.1.1.16.1.0 1 --> BIANCA-BRICK-MIBRES-MIB::CpuLoadSystem60s.1.0
# .1.3.6.1.4.1.272.4.17.4.1.1.17.1.0 9 --> BIANCA-BRICK-MIBRES-MIB::CpuLoadStreams60s.1.0


def discover_bintec_cpu(info):
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

    yield from check_cpu_util(util, params)


# Migration NOTE: Create a separate section, but a common check plug-in for
# tplink_cpu, hr_cpu, cisco_nexus_cpu, bintec_cpu, winperf_processor,
# lxc_container_cpu, docker_container_cpu.
# Migration via cmk/update_config.py!
def parse_bintec_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["bintec_cpu"] = LegacyCheckDefinition(
    name="bintec_cpu",
    parse_function=parse_bintec_cpu,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.272.4."),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.272.4.17.4.1.1",
        oids=["15", "16", "17"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_bintec_cpu,
    check_function=check_bintec_cpu,
    check_ruleset_name="cpu_utilization_os",
)
