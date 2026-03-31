#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.huawei.lib import (
    DETECT_HUAWEI_SWITCH,
    parse_huawei_physical_entity_values,
    Section,
)
from cmk.plugins.lib.cpu_util import check_cpu_util


def parse_huawei_switch_cpu(string_table: Sequence[StringTable]) -> Section:
    return parse_huawei_physical_entity_values(string_table)


def check_huawei_switch_cpu(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (item_data := section.get(item)):
        return

    # TODO: this weird. Either we should not discover in this case, or let it crash during checking.
    if item_data.value is None:
        return
    try:
        util = float(item_data.value)
    except TypeError:
        return
    yield from check_cpu_util(
        util=util,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
        cores=[("core1", util)],
    )


def discover_huawei_switch_cpu(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_huawei_switch_cpu = SNMPSection(
    name="huawei_switch_cpu",
    detect=DETECT_HUAWEI_SWITCH,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.31.1.1.1.1",
            oids=[OIDEnd(), "5"],
        ),
    ],
    parse_function=parse_huawei_switch_cpu,
)


check_plugin_huawei_switch_cpu = CheckPlugin(
    name="huawei_switch_cpu",
    service_name="CPU utilization %s",
    discovery_function=discover_huawei_switch_cpu,
    check_function=check_huawei_switch_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
