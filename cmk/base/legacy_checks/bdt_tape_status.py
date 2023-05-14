#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import contains, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree


def inventory_bdt_tape_status(info):
    return [(None, None)]


def check_bdt_tape_status(_no_item, _no_params, info):
    status_id = info[0][0]

    status = {
        "1": "other",
        "2": "unknown",
        "3": "ok",
        "4": "non-critical",
        "5": "critical",
        "6": "non-recoverable",
    }.get(status_id, "unknown")

    state = {
        "other": 3,
        "unknown": 3,
        "ok": 0,
        "non-critical": 1,
        "critical": 2,
        "non-recoverable": 2,
    }.get(status, 3)

    return state, status


check_info["bdt_tape_status"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20884.10893.2.101"),
    discovery_function=inventory_bdt_tape_status,
    check_function=check_bdt_tape_status,
    service_name="Tape Library Status",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20884.10893.2.101.2",
        oids=["1"],
    ),
)
