#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import contains, SNMPTree, StringTable


def inventory_bdtms_tape_info(info):
    return [(None, None)]


def check_bdtms_tape_info(_no_item, _no_params, info):
    _activity_id, health_id = info[0]

    health = {
        "1": "unknown",
        "2": "ok",
        "3": "warning",
        "4": "critical",
    }.get(health_id, "unknown")

    status = {
        "unknown": 3,
        "ok": 0,
        "warning": 1,
        "critical": 2,
    }.get(health, 3)

    return status, health


def parse_bdtms_tape_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["bdtms_tape_status"] = LegacyCheckDefinition(
    parse_function=parse_bdtms_tape_status,
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20884.77.83.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20884.2",
        oids=["1", "3"],
    ),
    service_name="Tape Library Status",
    discovery_function=inventory_bdtms_tape_info,
    check_function=check_bdtms_tape_info,
)
