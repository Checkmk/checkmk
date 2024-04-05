#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.agent_based.v2.type_defs import StringTable
from cmk.plugins.lib.sni_octopuse import DETECT_SNI_OCTOPUSE


def inventory_octopus_cpu(info):
    if len(info[0][0]) == 1:
        return [(None, None)]
    return []


def check_octopus_cpu(_no_item, _no_params_info, info):
    cpu_perc = int(info[0][0][0])
    perfdata = [("util", "%.3f" % cpu_perc)]
    return 0, "CPU utilization is %d%%" % cpu_perc, perfdata


def parse_sni_octopuse_cpu(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["sni_octopuse_cpu"] = LegacyCheckDefinition(
    parse_function=parse_sni_octopuse_cpu,
    detect=DETECT_SNI_OCTOPUSE,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.231.7.2.9.1",
            oids=["7"],
        )
    ],
    service_name="CPU utilization",
    discovery_function=inventory_octopus_cpu,
    check_function=check_octopus_cpu,
)
