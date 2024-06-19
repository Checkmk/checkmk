#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import any_of, equals, SNMPTree, StringTable

aironet_default_strength_levels = (-25, -20)
aironet_default_quality_levels = (40, 35)

# Note: this check uses three different items in order
# to distinguish three independent aspects. This should rather
# be converted to subchecks, because:
# - Subchecks can ship separate PNP templates.
# - Perf-O-Meters need separate checks, as well.
# - WATO configuration is done on a per-check basis and
#   the parameters for the three aspects are not of the same
#   meaing and type


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


def inventory_aironet_clients(info):
    if not info:
        return
    yield "strength", {}
    yield "quality", {}
    yield "clients", {}


def check_aironet_clients(item, _no_params, info):
    info = [line for line in info if line[0] != ""]

    if len(info) == 0:
        return (0, "No clients currently logged in")

    if item == "clients":
        return (
            0,
            "%d clients currently logged in" % len(info),
            [("clients", len(info), None, None, 0, None)],
        )

    # item = "quality" or "strength"
    if item == "quality":
        index = 1
        mmin = 0
        mmax = 100
        unit = "%"
        neg = 1
    else:
        index = 0
        mmin = None
        mmax = 0
        unit = "dB"
        neg = -1

    avg = sum(saveint(line[index]) for line in info) / float(len(info))
    warn, crit = (
        aironet_default_quality_levels if item == "quality" else aironet_default_strength_levels
    )
    perfdata = [(item, avg, warn, crit, mmin, mmax)]
    infotxt = f"signal {item} at {avg:.1f}{unit} (warn/crit at {warn}{unit}/{crit}{unit})"

    if neg * avg <= neg * crit:
        return (2, infotxt, perfdata)
    if neg * avg <= neg * warn:
        return (1, infotxt, perfdata)
    return (0, infotxt, perfdata)


def parse_aironet_clients(string_table: StringTable) -> StringTable:
    return string_table


check_info["aironet_clients"] = LegacyCheckDefinition(
    parse_function=parse_aironet_clients,
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.525"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.618"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.685"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.758"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1034"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1247"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1873"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1875"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1661"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2240"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.273.1.3.1.1",
        oids=["3", "4"],
    ),
    service_name="Average client signal %s",
    discovery_function=inventory_aironet_clients,
    check_function=check_aironet_clients,
)
