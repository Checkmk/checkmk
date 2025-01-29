#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.dell import DETECT_OPENMANAGE


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def inventory_dell_om_disks(section: StringTable) -> DiscoveryResult:
    yield from [Service(item=f"{x[3]}:{x[4]}:{x[5]}") for x in section]


def check_dell_om_disks(item: str, section: StringTable) -> CheckResult:
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

    for name, r_dstate, pid, eid, cid, tid, sizeMB, r_btype, r_sstate, r_smart, r_mt in section:
        ditem = f"{eid}:{cid}:{tid}"
        if ditem == item:
            state = State.OK
            dstate = saveint(r_dstate)
            btype = saveint(r_btype)
            sstate = saveint(r_sstate)
            smart = saveint(r_smart)
            mt = saveint(r_mt)
            size = saveint(sizeMB) * 1024 * 1024
            yield Result(state=State.OK, summary=f"{name} ({pid}, {render.bytes(size)})")

            if smart == 2:
                dstate = 34
            if dstate in [40, 35, 34, 26, 7, 4]:
                state = State.WARN
            elif dstate not in [3, 1, 13]:
                state = State.CRIT

            # handle hot spares as OK
            if sstate in [3, 4] and dstate == 1:
                state = State.OK

            yield Result(
                state=state, summary="state {}".format(pdisk_state.get(dstate, f"ukn ({dstate})"))
            )
            yield Result(
                state=State.OK, summary="Bus Type: %s" % bus_type.get(btype, f"unk ({btype})")
            )

            if sstate != 5:
                yield Result(
                    state=State.OK,
                    summary="Spare State: %s" % spare_state.get(sstate, "ukn (%s)" % sstate),
                )
            if mt != 0:
                yield Result(
                    state=State.OK, summary="Media Type: %s" % media_type.get(mt, "ukn (%s)" % mt)
                )

            return


def parse_dell_om_disks(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_om_disks = SimpleSNMPSection(
    name="dell_om_disks",
    detect=DETECT_OPENMANAGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10893.1.20.130.4.1",
        oids=["2", "4", "6", "9", "10", "15", "11", "21", "22", "31", "35"],
    ),
    parse_function=parse_dell_om_disks,
)
check_plugin_dell_om_disks = CheckPlugin(
    name="dell_om_disks",
    service_name="Physical Disk %s",
    discovery_function=inventory_dell_om_disks,
    check_function=check_dell_om_disks,
)
