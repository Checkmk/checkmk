#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# Parse the snmp data from the IBM agent.
# must be cautius since a failed disk makes the snmp output
# shift and gives false info for "slot_id"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, equals, exists, SNMPTree

check_info = {}


def parse_ibm_xraid_pdisks(info):
    data = {}
    for line in info:
        slot_id, disk_id, disk_type, disk_state, slot_desc = line
        if "slot" in slot_desc.lower():
            slot_id = int(slot_desc.split(", ")[-1][-1])
            enc_id = int(slot_desc.split(", ")[-2][-1])
            hba_id = int(slot_desc.split(", ")[-3][-1])
            disk_path = ("%d/%d/%d") % (hba_id, enc_id, slot_id)
            data.update({disk_path: (slot_id, disk_id, disk_type, disk_state, slot_desc)})
    return data


def discover_ibm_xraid_pdisks(section):
    return [(disk_id, None) for disk_id in section]


def check_ibm_xraid_pdisks(item, _no_params, section):
    for disk_path, disk_entry in section.items():
        if disk_path == item:
            _slot_label, _disk_id, _disk_type, disk_state, slot_desc = disk_entry
            if disk_state == "3":
                return (0, "Disk is active" + " [%s]" % slot_desc)
            if disk_state == "4":
                return (1, "Disk is rebuilding" + " [%s]" % slot_desc)
            if disk_state == "5":
                return (2, "Disk is dead" + " [%s]" % slot_desc)

    return (2, "disk is missing")  # + " [%s]" % data[item][4])


check_info["ibm_xraid_pdisks"] = LegacyCheckDefinition(
    name="ibm_xraid_pdisks",
    detect=all_of(
        any_of(
            equals(".1.3.6.1.2.1.1.1.0", "software: windows"), equals(".1.3.6.1.2.1.1.1.0", "linux")
        ),
        exists(".1.3.6.1.4.1.795.14.1.100.1.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.795.14.1",
        oids=["503.1.1.4", "400.1.1.1", "400.1.1.5", "400.1.1.11", "400.1.1.12"],
    ),
    parse_function=parse_ibm_xraid_pdisks,
    service_name="RAID PDisk %s",
    discovery_function=discover_ibm_xraid_pdisks,
    # there is no information about the ext mib in the right place
    # (at least on windows)
    # this means the check has to fetch a specific oid. Limit this
    # effect to relevant systems to lessen useless scanning.,
    check_function=check_ibm_xraid_pdisks,
)
