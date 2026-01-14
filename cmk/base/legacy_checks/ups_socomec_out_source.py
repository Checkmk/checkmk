#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.ups_socomec.lib import DETECT_SOCOMEC

check_info = {}


def discover_ups_socomec_out_source(info):
    if info:
        return [(None, None)]
    return []


def check_ups_socomec_out_source(_no_item, _no_params, info):
    # This is from the old (v5.01) MIB and is incompatible with the new one below
    #    ups_socomec_source_states = {
    #        1: (3, "Other"),
    #        2: (2, "Offline"),
    #        3: (0, "Normal"),
    #        4: (1, "Internal Maintenance Bypass"),
    #        5: (2, "On battery"),
    #        6: (0, "Booster"),
    #        7: (0, "Reducer"),
    #        8: (0, "Standby"),
    #        9: (0, "Eco mode"),
    #    }

    # This is from the new (v6) MIB
    ups_socomec_source_states = {
        1: (3, "Unknown"),
        2: (2, "On inverter"),
        3: (0, "On mains"),
        4: (0, "Eco mode"),
        5: (1, "On bypass"),
        6: (0, "Standby"),
        7: (1, "On maintenance bypass"),
        8: (2, "UPS off"),
        9: (0, "Normal mode"),
    }

    return ups_socomec_source_states[int(info[0][0])]


def parse_ups_socomec_out_source(string_table: StringTable) -> StringTable:
    return string_table


check_info["ups_socomec_out_source"] = LegacyCheckDefinition(
    name="ups_socomec_out_source",
    parse_function=parse_ups_socomec_out_source,
    detect=DETECT_SOCOMEC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.4",
        oids=["1"],
    ),
    service_name="Output Source",
    discovery_function=discover_ups_socomec_out_source,
    check_function=check_ups_socomec_out_source,
)
