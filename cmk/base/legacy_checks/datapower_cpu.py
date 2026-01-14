#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.plugins.datapower.lib import DETECT

check_info = {}


def discover_datapower_cpu(info):
    if info:
        yield None, {}


def check_datapower_cpu(_no_item, params, info):
    util = int(info[0][0])
    return check_cpu_util(util, params)


def parse_datapower_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["datapower_cpu"] = LegacyCheckDefinition(
    name="datapower_cpu",
    parse_function=parse_datapower_cpu,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.14",
        oids=["2"],
    ),
    service_name="CPU Utilization",
    discovery_function=discover_datapower_cpu,
    check_function=check_datapower_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
