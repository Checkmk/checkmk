#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.ups_in_voltage import check_ups_in_voltage
from cmk.plugins.ups_socomec.lib import DETECT_SOCOMEC

check_info = {}


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def discover_socomec_ups_in_voltage(info):
    yield from ((x[0], {}) for x in info if int(x[1]) > 0)


def check_socomec_ups_in_voltage(item, params, info):
    conv_info = []
    for line in info:
        conv_info.append([line[0], saveint(line[1]) // 10, line[1]])
    return check_ups_in_voltage(item, params, conv_info)


def parse_ups_socomec_in_voltage(string_table: StringTable) -> StringTable:
    return string_table


check_info["ups_socomec_in_voltage"] = LegacyCheckDefinition(
    name="ups_socomec_in_voltage",
    parse_function=parse_ups_socomec_in_voltage,
    detect=DETECT_SOCOMEC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.3.3.1",
        oids=["1", "2"],
    ),
    service_name="IN voltage phase %s",
    discovery_function=discover_socomec_ups_in_voltage,
    check_function=check_socomec_ups_in_voltage,
    check_ruleset_name="evolt",
    check_default_parameters={
        "levels_lower": (210.0, 180.0),
    },
)
