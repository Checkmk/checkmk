#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<ucs_bladecenter_topsystem:sep(9)>>>
# topSystem   Address 172.20.33.175   CurrentTime 2015-07-15T16:40:27.600 Ipv6Addr :: Mode cluster    Name svie23ucsfi01  SystemUpTime 125:16:10:53


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_ucs_bladecenter_topsystem(info):
    yield None, None


def check_ucs_bladecenter_topsystem(item, _no_params, info):
    for entry in info[0][1:]:
        tokens = entry.split(" ", 1)
        if len(tokens) == 2:
            yield 0, "%s: %s" % tuple(tokens)


def parse_ucs_bladecenter_topsystem(string_table: StringTable) -> StringTable:
    return string_table


check_info["ucs_bladecenter_topsystem"] = LegacyCheckDefinition(
    name="ucs_bladecenter_topsystem",
    parse_function=parse_ucs_bladecenter_topsystem,
    service_name="UCS TopSystem Info",
    discovery_function=discover_ucs_bladecenter_topsystem,
    check_function=check_ucs_bladecenter_topsystem,
)
