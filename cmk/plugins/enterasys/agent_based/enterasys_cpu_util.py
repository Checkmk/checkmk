#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.enterasys.lib import DETECT_ENTERASYS
from cmk.plugins.lib.cpu_util import check_cpu_util


def parse_enterasys_cpu_util(string_table: StringTable) -> StringTable:
    return string_table


def discover_enterasys_cpu_util(section: StringTable) -> DiscoveryResult:
    # [:-2] to remove the oid end
    for entry in section:
        yield Service(item=entry[0][:-2])


def check_enterasys_cpu_util(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for core, util in section:
        if item == core[:-2]:
            yield from check_cpu_util(
                util=int(util) / 10.0,
                params=params,
                value_store=get_value_store(),
                this_time=time.time(),
            )
            return


snmp_section_enterasys_cpu_util = SimpleSNMPSection(
    name="enterasys_cpu_util",
    detect=DETECT_ENTERASYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5624.1.2.49.1.1.1.1",
        oids=[OIDEnd(), "3"],
    ),
    parse_function=parse_enterasys_cpu_util,
)


check_plugin_enterasys_cpu_util = CheckPlugin(
    name="enterasys_cpu_util",
    service_name="CPU util %s",
    discovery_function=discover_enterasys_cpu_util,
    check_function=check_enterasys_cpu_util,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={
        "levels": (90.0, 95.0),
    },
)
