#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, LegacyCheckDefinition
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.ups_socomec import DETECT_SOCOMEC


def parse_ups_socomec_outphase(info):
    parsed = {}
    for index, rawvolt, rawcurr, rawload in info:
        parsed["Phase " + index] = {
            "voltage": (int(rawvolt) // 10, None),  # The actual precision does not appear to
            "current": (int(rawcurr) // 10, None),  # go beyond degrees, thus we drop the trailing 0
            "output_load": (int(rawload), None),
        }
    return parsed


def check_ups_socomec_outphase(item, params, parsed):
    if not item.startswith("Phase"):
        # fix item names discovered before 1.2.7
        item = "Phase %s" % item
    return check_elphase(item, params, parsed)


check_info["ups_socomec_outphase"] = LegacyCheckDefinition(
    detect=DETECT_SOCOMEC,
    parse_function=parse_ups_socomec_outphase,
    discovery_function=discover(),
    check_function=check_ups_socomec_outphase,
    service_name="Output %s",
    check_ruleset_name="ups_outphase",
    # Phase Index, Voltage/dV, Current/dA, Load/%
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.4.4.1",
        oids=["1", "2", "3", "4"],
    ),
    check_default_parameters={
        "voltage": (210, 200),
        "output_load": (80, 90),
    },
)
