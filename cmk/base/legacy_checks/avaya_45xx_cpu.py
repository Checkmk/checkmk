#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}


def discover_avaya_45xx_cpu(info):
    for idx, _line in enumerate(info):
        yield str(idx), {}


def check_avaya_45xx_cpu(item, params, info):
    now = time.time()
    for idx, used_perc in enumerate(info):
        if str(idx) == item:
            return check_cpu_util(int(used_perc[0]), params, now)
    return None


def parse_avaya_45xx_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["avaya_45xx_cpu"] = LegacyCheckDefinition(
    name="avaya_45xx_cpu",
    parse_function=parse_avaya_45xx_cpu,
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.45.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.45.1.6.3.8.1.1.5",
        oids=["3"],
    ),
    service_name="CPU utilization CPU %s",
    discovery_function=discover_avaya_45xx_cpu,
    check_function=check_avaya_45xx_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)
