#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.plugins.avaya.lib import DETECT_AVAYA

check_info = {}


def discover_avaya_88xx_cpu(info):
    return [(None, {})]


def check_avaya_88xx_cpu(_no_item, params, info):
    if not info:
        return None
    return check_cpu_util(int(info[0][0]), params, time.time())


def parse_avaya_88xx_cpu(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["avaya_88xx_cpu"] = LegacyCheckDefinition(
    name="avaya_88xx_cpu",
    parse_function=parse_avaya_88xx_cpu,
    detect=DETECT_AVAYA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.1",
        oids=["20"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_avaya_88xx_cpu,
    check_function=check_avaya_88xx_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (90.0, 95.0)},
)
