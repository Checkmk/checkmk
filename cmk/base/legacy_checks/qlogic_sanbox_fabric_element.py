#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, OIDEnd, SNMPTree, startswith, StringTable

check_info = {}


def discover_qlogic_sanbox_fabric_element(info):
    inventory = []
    for _fe_status, fe_id in info:
        inventory.append((fe_id, None))
    return inventory


def check_qlogic_sanbox_fabric_element(item, _no_params, info):
    for fe_status, fe_id in info:
        if fe_id == item:
            if fe_status == "1":
                return 0, "Fabric Element %s is online" % fe_id
            if fe_status == "2":
                return 2, "Fabric Element %s is offline" % fe_id
            if fe_status == "3":
                return 1, "Fabric Element %s is testing" % fe_id
            if fe_status == "4":
                return 2, "Fabric Element %s is faulty" % fe_id
            return 3, f"Fabric Element {fe_id} is in unidentified status {fe_status}"

    return 3, "No Fabric Element %s found" % item


def parse_qlogic_sanbox_fabric_element(string_table: StringTable) -> StringTable:
    return string_table


check_info["qlogic_sanbox_fabric_element"] = LegacyCheckDefinition(
    name="qlogic_sanbox_fabric_element",
    parse_function=parse_qlogic_sanbox_fabric_element,
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.14"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.8"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.75.1.1.4.1",
        oids=["4", OIDEnd()],
    ),
    service_name="Fabric Element %s",
    discovery_function=discover_qlogic_sanbox_fabric_element,
    check_function=check_qlogic_sanbox_fabric_element,
)
