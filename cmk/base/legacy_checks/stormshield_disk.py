#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.stormshield import DETECT_STORMSHIELD


def parse_stormshield_disk(info):
    standalone, cluster = info
    parsed = []
    if not cluster and not standalone:
        return []
    if cluster != []:
        for item in cluster:
            new_info = []
            index = item[0].split(".")[0]
            new_info.append(index)
            new_info.extend(item[1:])
            parsed.append(new_info)
        return parsed

    new_info = []
    new_info.append("0")
    new_info.extend(standalone[0])
    parsed.append(new_info)
    return parsed


def inventory_stormshield_disk(parsed):
    for disk in parsed:
        clusterindex = disk[0]
        yield clusterindex, {}


def check_stormshield_disk(item, params, parsed):
    for disk in parsed:
        clusterindex, index, name, selftest, israid, raidstatus, position = disk
        if item == clusterindex:
            infotext = "Device Index %s, Selftest: %s, Device Mount Point Name: %s" % (
                index,
                selftest,
                name,
            )
            if selftest != "PASSED":
                status = 1
            else:
                status = 0
            if israid != "0":
                infotext = infotext + ", Raid active, Raid Status %s, Disk Position %s" % (
                    raidstatus,
                    position,
                )
            yield status, infotext


check_info["stormshield_disk"] = LegacyCheckDefinition(
    detect=DETECT_STORMSHIELD,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.11256.1.11.11.1",
            oids=[OIDEnd(), "1", "2", "3", "4", "5", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.11256.1.10.5.1",
            oids=[OIDEnd(), "1", "2", "3", "4", "5", "6"],
        ),
    ],
    parse_function=parse_stormshield_disk,
    service_name="Disk %s",
    discovery_function=inventory_stormshield_disk,
    check_function=check_stormshield_disk,
)
