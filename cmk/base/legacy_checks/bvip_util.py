#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.plugins.bvip.lib import DETECT_BVIP

check_info = {}


def discover_bvip_util(info):
    if info:
        for name in ["Total", "Coder", "VCA"]:
            yield name, {}


def check_bvip_util(item, params, info):
    items = {
        "Total": 0,
        "Coder": 1,
        "VCA": 2,
    }

    usage = int(info[0][items[item]])
    if item == "Total":
        usage = 100 - usage
    return check_cpu_util(usage, params["levels"])


def parse_bvip_util(string_table: StringTable) -> StringTable:
    return string_table


check_info["bvip_util"] = LegacyCheckDefinition(
    name="bvip_util",
    parse_function=parse_bvip_util,
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1.9.1",
        oids=["1", "2", "3"],
    ),
    service_name="CPU utilization %s",
    discovery_function=discover_bvip_util,
    check_function=check_bvip_util,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)
