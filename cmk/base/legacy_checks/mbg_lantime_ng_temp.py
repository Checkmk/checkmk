#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.meinberg.liblantime import DETECT_MBG_LANTIME_NG

check_info = {}


def discover_mbg_lantime_ng_temp(info):
    if info:
        return [("System", {})]
    return []


def check_mbg_lantime_ng_temp(item, params, info):
    return check_temperature(float(info[0][0]), params, "mbg_lantime_ng_temp_%s" % item)


def parse_mbg_lantime_ng_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["mbg_lantime_ng_temp"] = LegacyCheckDefinition(
    name="mbg_lantime_ng_temp",
    parse_function=parse_mbg_lantime_ng_temp,
    detect=DETECT_MBG_LANTIME_NG,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.30.0.5.2",
        oids=["1"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_mbg_lantime_ng_temp,
    check_function=check_mbg_lantime_ng_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (80.0, 90.0),  # levels for system temperature
    },
)
