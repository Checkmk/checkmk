#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fsc import DETECT_FSC_SC2

check_info = {}

# .1.3.6.1.4.1.231.2.10.2.2.10.2.3.1.5.1 "PRIMERGY RX300 S8"
# .1.3.6.1.4.1.231.2.10.2.2.10.2.3.1.7.1 "--"
# .1.3.6.1.4.1.231.2.10.2.2.10.4.1.1.11.1 "V4.6.5.4 R1.6.0 for D2939-B1x"


def parse_fsc_sc2_info(string_table: StringTable) -> StringTable:
    return string_table


def discover_fsc_sc2_info(info):
    if info:
        return [(None, None)]
    return []


def check_fsc_sc2_info(_no_item, _no_params, info):
    if info:
        return (
            0,
            f"Model: {info[0][0]}, Serial Number: {info[0][1]}, BIOS Version: {info[0][2]}",
        )
    return None


check_info["fsc_sc2_info"] = LegacyCheckDefinition(
    name="fsc_sc2_info",
    parse_function=parse_fsc_sc2_info,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10",
        oids=["2.3.1.5.1", "2.3.1.7.1", "4.1.1.11.1"],
    ),
    service_name="Server Info",
    discovery_function=discover_fsc_sc2_info,
    check_function=check_fsc_sc2_info,
)
