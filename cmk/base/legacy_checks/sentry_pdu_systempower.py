#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, equals
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

# .1.3.6.1.4.1.1718.3.1.6.0 2111

# parsed = {
#  'Power Supply System': { 'power': (2111, None) }
# }


def parse_sentry_pdu_systempower(info):
    return {"Power Supply System": {"power": (int(info[0][0]), {})}}


check_info["sentry_pdu_systempower"] = {
    "detect": equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1718.3"),
    "parse_function": parse_sentry_pdu_systempower,
    "discovery_function": discover(),
    "check_function": check_elphase,
    "service_name": "%s",
    "check_ruleset_name": "el_inphase",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.1718.3.1",
        oids=["6"],
    ),
}
