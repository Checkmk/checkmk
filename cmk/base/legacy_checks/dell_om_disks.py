#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.config import check_info

from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_OPENMANAGE


def inventory_dell_om_disks(info):
    return [(f"{x[3]}:{x[4]}:{x[5]}", None) for x in info]


def check_dell_om_disks(item, _no_params, info):
    # State definitions. Found in check_openmange from Trond H. Amundsen
    spare_state = {
        1: "VD member",  # disk is a member of a virtual disk
        2: "DG member",  # disk is a member of a disk group
        3: "Global HS",  # disk is a global hot spare
        4: "Dedicated HS",  # disk is a dedicated hot spare
        5: "no",  # not a spare
    }

    media_type = {
        1: "unknown",
        2: "HDD",
        3: "SSD",
    }

    bus_type = {
        1: "SCSI",
        2: "IDE",
        3: "Fibre Channel",
        4: "SSA",
        6: "USB",
        7: "SATA",
        8: "SAS",
    }

    pdisk_state = {
        0: "Unknown",
        1: "Ready",
        2: "Failed",
        3: "Online",
        4: "Offline",
        6: "Degraded",
        7: "Recovering",
        11: "Removed",
        13: "non-raid",
        15: "Resynching",
        22: "Replacing",  # FIXME: this one is not defined in the OMSA MIBs
        24: "Rebuilding",
        25: "No Media",
        26: "Formatting",
        28: "Diagnostics",
        34: "Predictive failure",
        35: "Initializing",
        41: "Unsupported",
        53: "Incompatible",
        39: "Foreign",
        40: "Clear",
    }

    for name, dstate, pid, eid, cid, tid, sizeMB, btype, sstate, smart, mt in info:
        ditem = f"{eid}:{cid}:{tid}"
        if ditem == item:
            state = 0
            dstate = saveint(dstate)
            btype = saveint(btype)
            sstate = saveint(sstate)
            smart = saveint(smart)
            mt = saveint(mt)
            size = saveint(sizeMB) * 1024 * 1024
            msg = [f"{name} ({pid}, {render.bytes(size)})"]
            label = ""
            if smart == 2:
                dstate = 34
            if dstate in [40, 35, 34, 26, 7, 4]:
                state = 1
                label = "(!)"
            elif dstate not in [3, 1, 13]:
                state = 2
                label = "(!!)"

            # handle hot spares as OK
            if sstate in [3, 4] and dstate == 1:
                state = 0
                label = ""

            msg.append("state {}{}".format(pdisk_state.get(dstate, "ukn (%s)" % dstate), label))
            msg.append("Bus Type: %s" % bus_type.get(btype, "unk (%s)" % btype))

            if sstate != 5:
                msg.append("Spare State: %s" % spare_state.get(sstate, "ukn (%s)" % sstate))
            if mt != 0:
                msg.append("Media Type: %s" % media_type.get(mt, "ukn (%s)" % mt))

            return state, ", ".join(msg)
    return 3, "Device not found in SNMP tree"


def parse_dell_om_disks(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_om_disks"] = LegacyCheckDefinition(
    parse_function=parse_dell_om_disks,
    detect=DETECT_OPENMANAGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10893.1.20.130.4.1",
        oids=["2", "4", "6", "9", "10", "15", "11", "21", "22", "31", "35"],
    ),
    service_name="Physical Disk %s",
    discovery_function=inventory_dell_om_disks,
    check_function=check_dell_om_disks,
)
