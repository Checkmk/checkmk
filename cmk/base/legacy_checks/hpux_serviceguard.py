#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<hpux_serviceguard:sep(124)>>>
# summary=degraded
# node:hgs-sd1-srv2|summary=ok
# node:hgs-sd1-srv1|summary=ok
# node:hgs-sd2-srv1|summary=ok
# package:AKKP|summary=degraded
# package:ADBP|summary=degraded
# package:ADBT|summary=degraded
# package:KORRP|summary=degraded
# package:KVNAP|summary=degraded
# package:ARCP|summary=degraded
# package:AKKT|summary=degraded
# package:AVDT|summary=degraded
# package:KVNAB|summary=degraded
# package:AVDP|summary=degraded
# package:SDBP|summary=degraded


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def inventory_hpux_serviceguard(info):
    inventory = []
    for line in info:
        if len(line) == 1:
            item = "Total Status"
        else:
            item = line[0]
        inventory.append((item, None))
    return inventory


def check_hpux_serviceguard(item, _no_params, info):
    for line in info:
        if (item == "Total Status" and len(line) == 1) or (item == line[0] and len(line) == 2):
            status = line[-1].split("=")[-1]
            if status == "ok":
                code = 0
            elif status == "degraded":
                code = 1
            else:
                code = 2
            return (code, "state is %s" % status)

    return (3, "No such item found")


check_info["hpux_serviceguard"] = LegacyCheckDefinition(
    service_name="Serviceguard %s",
    discovery_function=inventory_hpux_serviceguard,
    check_function=check_hpux_serviceguard,
)
