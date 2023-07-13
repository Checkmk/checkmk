#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# example output


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith


def inventory_dell_idrac_raid(info):
    for index, _name, _status in info[0]:
        yield index, None


def check_dell_idrac_raid(item, _no_params, info):
    translate_status = {
        "1": (3, "other"),
        "2": (3, "unknown"),
        "3": (0, "OK"),
        "4": (1, "non-critical"),
        "5": (2, "critical"),
        "6": (2, "non-recoverable"),
    }

    for index, name, status in info[0]:
        if index == item:
            state, state_readable = translate_status[status]
            yield state, "Status of %s: %s" % (name, state_readable)


check_info["dell_idrac_raid"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10892.5"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.5.1.20.130.1.1",
            oids=["1", "2", "38"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.5.1.20.130.15.1",
            oids=["1", "4", "6", "21"],
        ),
    ],
    service_name="Raid Controller %s",
    discovery_function=inventory_dell_idrac_raid,
    check_function=check_dell_idrac_raid,
)


def inventory_dell_idrac_raid_bbu(info):
    for index, _status, _comp_status, _name in info[1]:
        yield index, None


def check_dell_idrac_raid_bbu(item, params, info):
    translate_bbu_status = {
        "1": (3, "UNKNOWN"),
        "2": (0, "READY"),
        "3": (2, "FAILED"),
        "4": (1, "DEGRADED"),
        "5": (3, "MISSING"),
        "6": (1, "CHARGING"),
        "7": (2, "BELOW THRESHOLD"),
    }

    for index, status, _comp_status, _name in info[1]:
        if index == item:
            state, state_readable = translate_bbu_status[status]
            yield state, "Battery status: %s" % state_readable


check_info["dell_idrac_raid.bbu"] = LegacyCheckDefinition(
    service_name="Raid BBU %s",
    sections=["dell_idrac_raid"],
    discovery_function=inventory_dell_idrac_raid_bbu,
    check_function=check_dell_idrac_raid_bbu,
)
