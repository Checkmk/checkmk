#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.elphase import check_elphase

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.apc import DETECT

check_info = {}

# .1.3.6.1.4.1.318.1.1.1.3.2.1.0 231


def parse_apc_symmetra_input(string_table):
    if not string_table:
        return {}
    return {
        "Input": {
            "voltage": float(string_table[0][0]),
        }
    }


def discover_apc_symmetra_input(section):
    yield from ((item, {}) for item in section)


check_info["apc_symmetra_input"] = LegacyCheckDefinition(
    name="apc_symmetra_input",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.1.3.2",
        oids=["1"],
    ),
    parse_function=parse_apc_symmetra_input,
    service_name="Phase %s",
    discovery_function=discover_apc_symmetra_input,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
)
