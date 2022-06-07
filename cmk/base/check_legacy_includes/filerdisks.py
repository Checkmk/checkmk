#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import get_bytes_human_readable

# disks = [
#     { "state" : "failed",
#       "identifier" : "Enclosure: 2, Slot: 1, Type: SATA",
#       "type" : "parity",
#       "capacity" : 1000000000000,
#     }

FILER_DISKS_CHECK_DEFAULT_PARAMETERS = {
    "failed_spare_ratio": (1.0, 50.0),
    "offline_spare_ratio": (1.0, 50.0),
}


def check_filer_disks(disks, params):  # pylint: disable=too-many-branches
    state: dict = {}
    state["prefailed"] = []
    state["failed"] = []
    state["offline"] = []
    state["spare"] = []

    total_capacity = 0

    for disk in disks:
        total_capacity += disk.get("capacity", 0)
        for what in state:
            if disk["state"] == what:
                state[what].append(disk)

    yield 0, "Total raw capacity: %s" % get_bytes_human_readable(total_capacity), [
        ("total_disk_capacity", total_capacity)
    ]
    # TODO: Is a prefailed disk unavailable?
    unavail_disks = len(state["prefailed"]) + len(state["failed"]) + len(state["offline"])
    yield 0, "Total disks: %d" % (len(disks) - unavail_disks), [("total_disks", len(disks))]

    spare_disks = len(state["spare"])
    spare_state, spare_infotext = 0, "Spare disks: %d" % spare_disks
    spare_disk_levels = params.get("number_of_spare_disks")
    if spare_disk_levels:
        warn, crit = spare_disk_levels
        if spare_disks < crit:
            spare_state = 2
        elif spare_disks < warn:
            spare_state = 1

        if spare_state:
            spare_infotext += " (warn/crit below %s/%s)" % (warn, crit)
    yield spare_state, spare_infotext, [("spare_disks", spare_disks)]

    parity_disks = [disk for disk in disks if disk["type"] == "parity"]
    prefailed_parity = [disk for disk in parity_disks if disk["state"] == "prefailed"]
    if len(parity_disks) > 0:
        yield 0, "Parity disks: %d (%d prefailed)" % (len(parity_disks), len(prefailed_parity))

    yield 0, "Failed disks: %d" % unavail_disks, [("failed_disks", unavail_disks)]

    for name, disk_type in [("Data", "data"), ("Parity", "parity")]:
        total_disks = [disk for disk in disks if disk["type"] == disk_type]
        prefailed_disks = [disk for disk in total_disks if disk["state"] == "prefailed"]
        if len(total_disks) > 0:
            info_text = "%s disks" % len(total_disks)
            if len(prefailed_disks) > 0:
                info_text += " (%d prefailed)" % (prefailed_disks)  # type: ignore[str-format]
            yield 0, info_text
            info_texts = []
            for disk in prefailed_disks:
                info_texts.append(disk["identifier"])
            if len(info_texts) > 0:
                yield 0, "%s Disk Details: %s" % (name, " / ".join(info_texts))

    for disk_state in ["failed", "offline"]:
        info_texts = []
        for disk in state[disk_state]:
            info_texts.append(disk["identifier"])
        if len(info_texts) > 0:
            yield 0, "%s Disk Details: %s" % (disk_state, " / ".join(info_texts))
            warn, crit = params["%s_spare_ratio" % disk_state]
            ratio = (
                float(len(state[disk_state])) / (len(state[disk_state]) + len(state["spare"])) * 100
            )
            return_state: bool | int = False
            if ratio >= crit:
                return_state = 2
            elif ratio >= warn:
                return_state = 1
            if return_state:
                yield return_state, "Too many %s disks (warn/crit at %.1f%%/%.1f%%)" % (
                    disk_state,
                    warn,
                    crit,
                )
