#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# Put here the example output from your TCP-Based agent. If the
# check is SNMP-Based, then remove this section


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

check_info = {}


def parse_tsm_scratch(string_table):
    parsed = {}
    for line in string_table:
        if len(line) != 3:
            continue

        inst, tapes, library = line
        try:
            num_tapes = int(tapes)
        except ValueError:
            continue

        if inst != "default":
            item = f"{inst} / {library}"
        else:
            item = library

        parsed[item] = num_tapes
    return parsed


def inventory_tsm_scratch(parsed):
    return [(lib, {}) for lib in parsed]


def check_tsm_scratch(item, _no_params, parsed):
    num_tapes = parsed.get(item)
    if num_tapes is None:
        return None
    return check_levels(
        num_tapes,
        "tapes_free",
        (None, None, 7, 5),
        human_readable_func=lambda x: "%d" % x,
        infoname="Found tapes",
    )


check_info["tsm_scratch"] = LegacyCheckDefinition(
    name="tsm_scratch",
    parse_function=parse_tsm_scratch,
    service_name="Scratch Pool %s",
    discovery_function=inventory_tsm_scratch,
    check_function=check_tsm_scratch,
)
