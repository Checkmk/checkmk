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


def parse_raritan_pdu_inlet(string_table):
    precisions = {oid_end: int(decimals) for oid_end, decimals in string_table[0]}
    parsed: dict[str, dict[str, tuple[str, tuple | None]]] = {}
    for oid_end, availability, sensor_state, value in string_table[1]:
        if availability == "1":
            phase_id, sensor_type = oid_end.split(".")[2:4]
            phase = "Phase " + phase_id
            if sensor_type in raritan_map_type:
                parsed.setdefault(phase, {})
                key, _key_info = raritan_map_type[sensor_type]  # get key for elphase.include
                value = float(value) / 10 ** precisions[oid_end]
                state, state_info = raritan_map_state[sensor_state]

                if state > 0:
                    parsed[phase][key] = (value, (state, state_info))
                else:
                    parsed[phase][key] = (value, None)
    return parsed


def check_raritan_pdu_inlet(item, params, info):
    if not item.startswith("Phase"):
        item = "Phase %s" % item
    yield from check_elphase(item, params, info)


def discover_raritan_pdu_inlet(section):
    yield from ((item, {}) for item in section)


check_info["raritan_pdu_inlet"] = LegacyCheckDefinition(
    name="raritan_pdu_inlet",
    detect=DETECT_RARITAN,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.3.3.6.1",
            oids=[OIDEnd(), "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.13742.6.5.2.4.1",
            oids=[OIDEnd(), "2", "3", "4"],
        ),
    ],
    parse_function=parse_raritan_pdu_inlet,
    service_name="Input %s",
    discovery_function=discover_raritan_pdu_inlet,
    check_function=check_raritan_pdu_inlet,
    check_ruleset_name="el_inphase",
)
