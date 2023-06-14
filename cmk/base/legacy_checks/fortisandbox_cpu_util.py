#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.fortinet import DETECT_FORTISANDBOX

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


check_info["fortisandbox_cpu_util"] = LegacyCheckDefinition(
    detect=DETECT_FORTISANDBOX,
    discovery_function=discover_fortisandbox_cpu_util,
    check_function=check_fortisandbox_cpu_util,
    service_name="CPU utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.118.3.1",
        oids=["3"],
    ),
    check_ruleset_name="cpu_utilization",
)
