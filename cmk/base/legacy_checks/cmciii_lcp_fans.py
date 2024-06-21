#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.cmciii import DETECT_CMCIII_LCP


def inventory_cmciii_lcp_fans(info):
    inventory = []
    # FAN infos have 4 elements. Split the single info line we get
    # into even sized chunks of 4 elements. In some cases there might
    # be non-fan information in the resulting data like infos about
    # water cooling. Filter them out.
    parts = [info[0][x + 1 : x + 4] for x in range(0, len(info[0]), 4)]
    for i, (name, _value, status) in enumerate(parts):
        if status != "off" and "FAN" in name:
            # FIXME: Why not use the unique name? Maybe recode
            inventory.append((str(i + 1), None))
    return inventory


def check_cmciii_lcp_fans(item, params, info):
    lowlevel = int(re.sub(" .*$", "", info[0][0]))  # global low warning

    parts = [info[0][x + 1 : x + 4] for x in range(0, len(info[0]), 4)]
    for i, (name, value, status) in enumerate(parts):
        if str(i) == item:
            rpm, unit = value.split(" ", 1)
            rpm = int(rpm)

            sym = ""
            if status == "OK" and rpm >= lowlevel:
                state = 0
            elif status == "OK" and rpm < lowlevel:
                state = 1
                sym = "(!)"
            else:
                state = 2
                sym = "(!!)"

            info_text = "%s RPM: %d%s (limit %d%s)%s, Status %s" % (
                name,
                rpm,
                unit,
                lowlevel,
                unit,
                sym,
                status,
            )

            perfdata = [("rpm", str(rpm) + unit, str(lowlevel) + ":", 0, 0)]

            return (state, info_text, perfdata)
    return None


def parse_cmciii_lcp_fans(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["cmciii_lcp_fans"] = LegacyCheckDefinition(
    parse_function=parse_cmciii_lcp_fans,
    detect=DETECT_CMCIII_LCP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2606.7.4.2.2.1.10.2",
        oids=[
            "34",
            "35",
            "36",
            "37",
            "38",
            "39",
            "40",
            "41",
            "42",
            "43",
            "44",
            "45",
            "46",
            "47",
            "48",
            "49",
            "50",
            "51",
            "52",
            "53",
            "54",
            "55",
            "56",
            "57",
        ],
    ),
    service_name="LCP Fanunit FAN %s",
    discovery_function=inventory_cmciii_lcp_fans,
    check_function=check_cmciii_lcp_fans,
)
