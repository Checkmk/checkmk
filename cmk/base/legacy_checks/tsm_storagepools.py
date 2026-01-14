#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<tsm_storagepool>>>
# tsmfarm2      Bkup      LTOBACK               1399378.64
# tsmfarm2      Arch      LTOARCHCOPY            157288.14

# <<<tsm_storagepool>>>
# default        Bkup      VP4200.GOLD                                                254776345.58^M
# default        Bkup      VP4200.TDP                                                 204386407.76^M
# default        Bkup      VP860.CM                                                   122661787.24^M
# default                  DPC.EXC.2013                                                           ^M
# default                  DPC.EXC.CM                                                             ^M
# default                  DPC.EXCDAG                                                             ^M
# default                  DPC.GOLD.ALL                                                           ^M
# default                  DPC.GOLD.UNIX                                                          ^M
# default                  DPC.GOLD.VE


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render

check_info = {}


def parse_tsm_storagepools(string_table):
    parsed = {}
    for line in string_table:
        if len(line) < 4:
            continue

        inst, stype, name, size = line[:4]
        if inst == "default":
            item = name
        else:
            item = inst + " / " + name
        parsed.setdefault(item, {"type": stype, "size": size.replace(",", ".")})

    return parsed


def discover_tsm_storagepools(parsed):
    for inst in parsed:
        yield inst, None


def check_tsm_storagepools(item, _no_params, parsed):
    if item not in parsed:
        return 3, "no such storage pool"

    data = parsed[item]
    stype = data["type"]
    size = int(float(data["size"]) * 1024**2)
    return (
        0,
        f"Used size: {render.disksize(size)}, Type: {stype}",
        [("used_space", size)],
    )


check_info["tsm_storagepools"] = LegacyCheckDefinition(
    name="tsm_storagepools",
    parse_function=parse_tsm_storagepools,
    service_name="TSM Storagepool %s",
    discovery_function=discover_tsm_storagepools,
    check_function=check_tsm_storagepools,
)
