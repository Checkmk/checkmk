#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.check_legacy_includes.raritan import raritan_map_state, raritan_map_type

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.plugins.lib.raritan import DETECT_RARITAN

check_info = {}


def parse_raritan_pdu_inlet_summary(string_table):
    summary: dict[str, tuple] = {}
    for sensor_type, decimal_digits, availability, sensor_state, value in string_table:
        if availability == "1":
            if sensor_type in raritan_map_type:  # handled sensor types
                key, _key_info = raritan_map_type[sensor_type]  # get key for elphase.include
                value = float(value) / 10 ** int(decimal_digits)
                state, state_info = raritan_map_state[sensor_state]

                if state > 0:
                    summary[key] = (value, (state, state_info))
                else:
                    summary[key] = (value, None)

    return {"Summary": summary} if summary else None


def discover_raritan_pdu_inlet_summary(section):
    yield from ((item, {}) for item in section)


check_info["raritan_pdu_inlet_summary"] = LegacyCheckDefinition(
    name="raritan_pdu_inlet_summary",
    detect=DETECT_RARITAN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6",
        oids=[OIDEnd(), "3.3.4.1.7.1.1", "5.2.3.1.2.1.1", "5.2.3.1.3.1.1", "5.2.3.1.4.1.1"],
    ),
    parse_function=parse_raritan_pdu_inlet_summary,
    service_name="Input %s",
    discovery_function=discover_raritan_pdu_inlet_summary,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
)
