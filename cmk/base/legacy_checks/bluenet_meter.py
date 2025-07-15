#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_legacy_includes.elphase import check_elphase

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith

check_info = {}


def parse_bluenet_meter(string_table):
    parsed = {}
    for meter_id, power_p, power_s, u_rms, i_rms in string_table:
        # do not take into account powermeters with no voltage
        if u_rms != "0":
            parsed.setdefault(meter_id, {})
            parsed[meter_id]["voltage"] = float(u_rms) / 1000.0, None
            parsed[meter_id]["current"] = float(i_rms) / 1000.0, None
            parsed[meter_id]["power"] = float(power_p), None
            parsed[meter_id]["appower"] = float(power_s), None
    return parsed


def discover_bluenet_meter(section):
    yield from ((item, {}) for item in section)


check_info["bluenet_meter"] = LegacyCheckDefinition(
    name="bluenet_meter",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21695.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21695.1.10.7.2.1",
        oids=["1", "5", "7", "8", "9"],
    ),
    parse_function=parse_bluenet_meter,
    service_name="Powermeter %s",
    discovery_function=discover_bluenet_meter,
    check_function=check_elphase,
    check_ruleset_name="ups_outphase",
)
