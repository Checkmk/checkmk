#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import any_of, equals, SNMPTree, StringTable


def inventory_bintec_info(info):
    if info and info[0]:
        yield None, {}


def check_bintec_info(checktype, params, info):
    if len(info[0]) < 2:
        return (3, "No data retrieved")
    sw_version, serial = info[0]
    return (0, f"Serial: {serial}, Software: {sw_version}")


# 1.3.6.1.4.1.272.4.1.26.0 SW Version
# 1.3.6.1.4.1.272.4.1.31.0 S/N

# This check works on all SNMP hosts


def parse_bintec_info(string_table: StringTable) -> StringTable:
    return string_table


check_info["bintec_info"] = LegacyCheckDefinition(
    parse_function=parse_bintec_info,
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.272.4.200.83.88.67.66.0.0"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.272.4.158.82.78.66.48.0.0"),
    ),
    # 1.3.6.1.4.1.272.4.1.31.0 S/N
    # 1.3.6.1.4.1.272.4.1.26.0 SW Version,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.272.4.1",
        oids=["26.0", "31.0"],
    ),
    service_name="Bintec Info",
    discovery_function=inventory_bintec_info,
    check_function=check_bintec_info,
)
