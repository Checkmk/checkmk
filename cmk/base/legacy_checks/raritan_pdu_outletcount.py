#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, SNMPTree, startswith, StringTable

check_info = {}


def discover_raritan_pdu_outletcount(info):
    if info and info[0]:
        yield None, {}


def check_raritan_pdu_outletcount(item, params, info):
    levels = params.get("levels_upper", (None, None)) + params.get("levels_lower", (None, None))
    try:
        yield check_levels(
            int(info[0][0]), "outletcount", levels, human_readable_func=lambda f: "%.f" % f
        )
    except IndexError:
        pass


def parse_raritan_pdu_outletcount(string_table: StringTable) -> StringTable:
    return string_table


check_info["raritan_pdu_outletcount"] = LegacyCheckDefinition(
    name="raritan_pdu_outletcount",
    parse_function=parse_raritan_pdu_outletcount,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.6"),
        any_of(
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX2-2"),
            startswith(".1.3.6.1.4.1.13742.6.3.2.1.1.3.1", "PX3"),
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.6.3.2.2.1.4",
        oids=["1"],
    ),
    service_name="Outlet Count",
    discovery_function=discover_raritan_pdu_outletcount,
    check_function=check_raritan_pdu_outletcount,
    check_ruleset_name="plug_count",
    check_default_parameters={},
)
