#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.mbg_lantime import (
    check_mbg_lantime_state_common,
    MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS,
)
from cmk.plugins.meinberg.liblantime import DETECT_MBG_LANTIME_NG

check_info = {}


def discover_mbg_lantime_ng_state(info):
    if info:
        return [(None, {})]
    return []


def check_mbg_lantime_ng_state(_no_item, params, info):
    states = {
        "0": (2, "not available"),
        "1": (2, "not synchronized"),
        "2": (0, "synchronized"),
    }
    ntp_state, stratum, refclock_name, refclock_offset_str = info[0]
    # Convert from milliseconds to microseconds
    # make sure, we don't try to parse "n/a" but pass 0 instead, because check_mbg_lantime_state_common()
    # also tries to parse it as float
    refclock_offset = (
        refclock_offset_str
        if refclock_offset_str == "n/a"
        else float(refclock_offset_str.lstrip("=")) * 1000
    )
    newinfo = [[ntp_state, stratum, refclock_name.lstrip("="), refclock_offset]]
    return check_mbg_lantime_state_common(states, params["stratum"], params["offset"], newinfo)


def parse_mbg_lantime_ng_state(string_table: StringTable) -> StringTable:
    return string_table


check_info["mbg_lantime_ng_state"] = LegacyCheckDefinition(
    name="mbg_lantime_ng_state",
    parse_function=parse_mbg_lantime_ng_state,
    detect=DETECT_MBG_LANTIME_NG,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.30.0.2",
        oids=["1", "2", "3", "4"],
    ),
    service_name="LANTIME State",
    discovery_function=discover_mbg_lantime_ng_state,
    check_function=check_mbg_lantime_ng_state,
    check_ruleset_name="mbg_lantime_state",
    check_default_parameters=MBG_LANTIME_STATE_CHECK_DEFAULT_PARAMETERS,
)
