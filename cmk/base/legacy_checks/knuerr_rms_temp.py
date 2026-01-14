#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.knuerr.lib import DETECT_KNUERR

check_info = {}


def discover_knuerr_rms_temp(info):
    return [("Ambient", {})]


def check_knuerr_rms_temp(_no_item, params, info):
    return check_temperature(float(info[0][0]) / 10, params, "knuerr_rms_temp")


def parse_knuerr_rms_temp(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["knuerr_rms_temp"] = LegacyCheckDefinition(
    name="knuerr_rms_temp",
    parse_function=parse_knuerr_rms_temp,
    detect=DETECT_KNUERR,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3711.15.1.1.1.1",
        oids=["4"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_knuerr_rms_temp,
    check_function=check_knuerr_rms_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
    },
)
