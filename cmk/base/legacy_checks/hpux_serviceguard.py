#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

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


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_hpux_serviceguard(info):
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


def parse_hpux_serviceguard(string_table: StringTable) -> StringTable:
    return string_table


check_info["hpux_serviceguard"] = LegacyCheckDefinition(
    name="hpux_serviceguard",
    parse_function=parse_hpux_serviceguard,
    service_name="Serviceguard %s",
    discovery_function=discover_hpux_serviceguard,
    check_function=check_hpux_serviceguard,
)
