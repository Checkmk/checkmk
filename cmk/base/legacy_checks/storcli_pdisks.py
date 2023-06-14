#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils import megaraid


def parse_storcli_pdisks(info):
    parsed = {}

    controller_num = 0
    separator_count = 0
    for line in info:
        if line[0].startswith("-----"):
            separator_count += 1
        elif separator_count == 2:
            eid_and_slot, device, state, _drivegroup, size, size_unit = line[:6]
            parsed["C%i.%s-%s" % (controller_num, eid_and_slot, device)] = {
                "state": megaraid.expand_abbreviation(state),
                "size": (float(size), size_unit),
            }
        if separator_count == 3:
            # each controller has 3 separators, reset count and continue
            separator_count = 0
            controller_num += 1

    return parsed


def inventory_storcli_pdisks(parsed):
    for item in parsed:
        yield (item, {})


def check_storcli_pdisks(item, params, parsed):
    if item not in parsed:
        return None

    infotext = "Size: %f %s" % parsed[item]["size"]

    diskstate = parsed[item]["state"]
    infotext += ", Disk State: %s" % diskstate

    status = params.get(diskstate, 3)

    return status, infotext


check_info["storcli_pdisks"] = LegacyCheckDefinition(
    parse_function=parse_storcli_pdisks,
    discovery_function=inventory_storcli_pdisks,
    check_function=check_storcli_pdisks,
    service_name="RAID PDisk EID:Slot-Device %s",
    check_ruleset_name="storcli_pdisks",
    check_default_parameters=megaraid.PDISKS_DEFAULTS,
)
