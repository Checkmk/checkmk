#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, equals, SNMPTree, StringTable
from cmk.base.check_legacy_includes.uptime import check_uptime_seconds

check_info = {}

# .1.3.6.1.4.1.9.9.441.1.3.1 CISCO-SRST-MIB::csrstState (1: active, 2: inactive)
# .1.3.6.1.4.1.9.9.441.1.3.4 CISCO-SRST-MIB::csrstTotalUpTime


def discover_cisco_srst_state(info):
    return [(None, None)]


def check_cisco_srst_state(_no_item, _no_params, info):
    srst_state, uptime_text = info[0]

    # Check the state
    if srst_state == "1":
        yield 2, "SRST active"
    else:
        yield 0, "SRST inactive"

    # Display SRST uptime
    yield check_uptime_seconds(None, int(uptime_text) * 60)


def parse_cisco_srst_state(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["cisco_srst_state"] = LegacyCheckDefinition(
    name="cisco_srst_state",
    parse_function=parse_cisco_srst_state,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), equals(".1.3.6.1.4.1.9.9.441.1.2.1.0", "1")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.441.1.3",
        oids=["1", "4"],
    ),
    service_name="SRST State",
    discovery_function=discover_cisco_srst_state,
    check_function=check_cisco_srst_state,
)
