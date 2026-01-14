#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.plugins.knuerr.lib import DETECT_KNUERR

check_info = {}


def discover_knuerr_rms_humidity(info):
    yield None, {}


def check_knuerr_rms_humidity(_no_item, params, info):
    _name, reading = info[0]
    return check_humidity(float(reading) / 10, params)


def parse_knuerr_rms_humidity(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["knuerr_rms_humidity"] = LegacyCheckDefinition(
    name="knuerr_rms_humidity",
    parse_function=parse_knuerr_rms_humidity,
    detect=DETECT_KNUERR,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3711.15.1.1.1.2",
        oids=["2", "4"],
    ),
    service_name="Humidity",
    discovery_function=discover_knuerr_rms_humidity,
    check_function=check_knuerr_rms_humidity,
    check_ruleset_name="single_humidity",
    check_default_parameters={
        "levels_lower": (40, 30),
        "levels": (70, 75),
    },
)
