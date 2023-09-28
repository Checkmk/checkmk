#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# 2019-01-07, comNET GmbH, Fabian Binder


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

MAP_RPO_STATES = {
    "0": (1, "VPG is initializing"),
    "1": (0, "Meeting SLA specification"),
    "2": (2, "Not meeting SLA specification for RPO SLA and journal history"),
    "3": (2, "Not meeting SLA specification for RPO SLA"),
    "4": (2, "Not meeting SLA specification for journal history"),
    "5": (1, "VPG is in a failover operation"),
    "6": (1, "VPG is in a move operation"),
    "7": (1, "VPG is being deleted"),
    "8": (1, "VPG has been recovered"),
}


def parse_zerto_vpg(string_table):
    parsed = {}
    for line in string_table:
        if len(line) < 3:
            continue
        vpgname = line[0]
        vpg = parsed.setdefault(vpgname, {})
        vpg["state"] = line[1]
        vpg["actual_rpo"] = line[2]
    return parsed


def check_zerto_vpg_rpo(item, _params, parsed):
    if not (data := parsed.get(item)):
        return
    state, vpg_info = MAP_RPO_STATES.get(data.get("state"), (3, "Unknown"))
    yield state, "VPG Status: %s" % vpg_info


def discover_zerto_vpg_rpo(section):
    yield from ((item, {}) for item in section)


check_info["zerto_vpg_rpo"] = LegacyCheckDefinition(
    parse_function=parse_zerto_vpg,
    service_name="Zerto VPG RPO %s",
    discovery_function=discover_zerto_vpg_rpo,
    check_function=check_zerto_vpg_rpo,
    check_ruleset_name="zerto_vpg_rpo",
)
