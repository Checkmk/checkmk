#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def discover_ipr400_temp(info):
    if len(info) > 0:
        yield "Ambient", None


def check_ipr400_temp(item, params, info):
    return check_temperature(int(info[0][0]), params, "ipr400_temp_%s" % item)


def parse_ipr400_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["ipr400_temp"] = LegacyCheckDefinition(
    name="ipr400_temp",
    parse_function=parse_ipr400_temp,
    detect=startswith(".1.3.6.1.2.1.1.1.0", "ipr voip device ipr400"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.27053.1.4.5",
        oids=["9"],
    ),
    service_name="Temperature %s ",
    discovery_function=discover_ipr400_temp,
    check_function=check_ipr400_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 40.0),  # reported temperature seems to be near room temperature usually
    },
)
