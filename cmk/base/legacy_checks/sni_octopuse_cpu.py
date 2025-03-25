#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.sni_octopuse import DETECT_SNI_OCTOPUSE

check_info = {}


def discover_octopus_cpu(section: StringTable) -> DiscoveryResult:
    if len(section[0]) == 1:
        yield Service()


def check_octopus_cpu(_no_item, _no_params_info, info):
    cpu_perc = int(info[0][0])
    perfdata = [("util", "%.3f" % cpu_perc)]
    return 0, "CPU utilization is %d%%" % cpu_perc, perfdata


def parse_sni_octopuse_cpu(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["sni_octopuse_cpu"] = LegacyCheckDefinition(
    name="sni_octopuse_cpu",
    parse_function=parse_sni_octopuse_cpu,
    detect=DETECT_SNI_OCTOPUSE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.7.2.9.1",
        oids=["7"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_octopus_cpu,
    check_function=check_octopus_cpu,
)
