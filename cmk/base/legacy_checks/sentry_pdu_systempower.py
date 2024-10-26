#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.elphase import check_elphase

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, SNMPTree

check_info = {}

# .1.3.6.1.4.1.1718.3.1.6.0 2111

# parsed = {
#  'Power Supply System': { 'power': (2111, None) }
# }


def parse_sentry_pdu_systempower(string_table):
    return (
        {"Power Supply System": {"power": (int(string_table[0][0]), {})}} if string_table else None
    )


def discover_sentry_pdu_systempower(section):
    yield from ((item, {}) for item in section)


check_info["sentry_pdu_systempower"] = LegacyCheckDefinition(
    name="sentry_pdu_systempower",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1718.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1718.3.1",
        oids=["6"],
    ),
    parse_function=parse_sentry_pdu_systempower,
    service_name="%s",
    discovery_function=discover_sentry_pdu_systempower,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
)
