#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.plugins.stulz.lib import DETECT_STULZ

check_info = {}


def savefloat(f: str) -> float:
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


def discover_stulz_humidity(info):
    return [(x[0], {}) for x in info]


def check_stulz_humidity(item, params, info):
    for line in info:
        if line[0] == item:
            return check_humidity(savefloat(line[1]) / 10, params)
    return None


def parse_stulz_humidity(string_table: StringTable) -> StringTable:
    return string_table


check_info["stulz_humidity"] = LegacyCheckDefinition(
    name="stulz_humidity",
    parse_function=parse_stulz_humidity,
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.1.1.1.2.1.1.1194",
        oids=[OIDEnd(), "1"],
    ),
    service_name="Humidity %s ",
    discovery_function=discover_stulz_humidity,
    check_function=check_stulz_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (60.0, 65.0),
        "levels_lower": (40.0, 35.0),
    },
)
