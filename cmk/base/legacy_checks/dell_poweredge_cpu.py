#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.base.check_legacy_includes.dell_poweredge import check_dell_poweredge_cpu

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_IDRAC_POWEREDGE

check_info = {}


def inventory_dell_poweredge_cpu(info):
    for _chassisIndex, _Index, StateSettings, _Status, LocationName in info[0]:
        if LocationName != "" and StateSettings != "1":
            yield LocationName, None


def parse_dell_poweredge_cpu(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["dell_poweredge_cpu"] = LegacyCheckDefinition(
    name="dell_poweredge_cpu",
    parse_function=parse_dell_poweredge_cpu,
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.4.1100.32.1",
            oids=["1", "2", "4", "5", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.4.1100.30.1",
            oids=["1", "2", "23"],
        ),
    ],
    service_name="%s",
    discovery_function=inventory_dell_poweredge_cpu,
    check_function=check_dell_poweredge_cpu,
)
