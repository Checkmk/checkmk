#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.plugins.lib.fortinet import DETECT_FORTISANDBOX

check_info = {}

# Nikolas Hagemann, comNET GmbH - nikolas.hagemann@comnetgmbh.com

# Example output:
# .1.3.6.1.4.1.12356.118.3.1.3.0 10

Section = StringTable


def discover_fortisandbox_cpu_util(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_fortisandbox_cpu_util(_no_item, params, info):
    if not info:
        return None
    util = int(info[0][0])
    return check_cpu_util(util, params)


def parse_fortisandbox_cpu_util(string_table: StringTable) -> StringTable:
    return string_table


check_info["fortisandbox_cpu_util"] = LegacyCheckDefinition(
    name="fortisandbox_cpu_util",
    parse_function=parse_fortisandbox_cpu_util,
    detect=DETECT_FORTISANDBOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.118.3.1",
        oids=["3"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_fortisandbox_cpu_util,
    check_function=check_fortisandbox_cpu_util,
    check_ruleset_name="cpu_utilization",
)
