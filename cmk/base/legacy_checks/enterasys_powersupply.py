#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# MIB structure:
# 1.3.6.1.4.1.52.4.3.1.2.1.1.1    ctChasPowerSupplyNum
# 1.3.6.1.4.1.52.4.3.1.2.1.1.2    ctChasPowerSupplyState
# 1.3.6.1.4.1.52.4.3.1.2.1.1.3    ctChasPowerSupplyType
# 1.3.6.1.4.1.52.4.3.1.2.1.1.4    ctChasPowerSupplyRedundancy


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.enterasys.lib import DETECT_ENTERASYS

check_info = {}


def discover_enterasys_powersupply(info):
    inventory = []
    for num, state, _typ, _redun in info:
        if state == "3":
            inventory.append((num, {}))
    return inventory


def check_enterasys_powersupply(item, params, info):
    supply_types = {
        "1": "ac-dc",
        "2": "dc-dc",
        "3": "notSupported",
        "4": "highOutput",
    }
    redundancy_types = {
        "1": "redundant",
        "2": "notRedundant",
        "3": "notSupported",
    }

    for num, state, typ, redun in info:
        if num == item:
            if state == "4":
                return 2, "Status: installed and not operating"

            redun_mapped = redundancy_types.get(redun, "unknown[%s]" % redun)
            if redun and int(redun) in params["redundancy_ok_states"]:
                return 0, "Status: working and {} ({})".format(
                    redun_mapped,
                    supply_types.get(typ, "unknown[%s]" % typ),
                )
            return 1, "Status: %s" % redun_mapped
    return None


def parse_enterasys_powersupply(string_table: StringTable) -> StringTable:
    return string_table


check_info["enterasys_powersupply"] = LegacyCheckDefinition(
    name="enterasys_powersupply",
    parse_function=parse_enterasys_powersupply,
    detect=DETECT_ENTERASYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.52.4.3.1.2.1.1",
        oids=[OIDEnd(), "2", "3", "4"],
    ),
    service_name="PSU %s",
    discovery_function=discover_enterasys_powersupply,
    check_function=check_enterasys_powersupply,
    check_ruleset_name="enterasys_powersupply",
    check_default_parameters={
        "redundancy_ok_states": [
            1,
        ],
    },
)
