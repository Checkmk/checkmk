#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    render,
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


def parse_huawei_switch_mem(string_table: Sequence[StringTable]) -> Section:
    return parse_huawei_physical_entity_values(string_table)


def check_huawei_switch_mem(
    item: str, params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    if not (item_data := section.get(item)):
        return

    # TODO: this weird. Either we should not discover in this case, or let it crash during checking.
    if item_data.value is None:
        return
    try:
        mem = float(item_data.value)
    except TypeError:
        return

    yield from check_levels(
        mem,
        levels_upper=params.get("levels"),
        metric_name="mem_used_percent",
        render_func=render.percent,
        label="Usage",
    )


def discover_huawei_switch_mem(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_huawei_switch_mem = SNMPSection(
    name="huawei_switch_mem",
    detect=DETECT_HUAWEI_SWITCH,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.31.1.1.1.1",
            oids=[OIDEnd(), "7"],
        ),
    ],
    parse_function=parse_huawei_switch_mem,
)


check_plugin_huawei_switch_mem = CheckPlugin(
    name="huawei_switch_mem",
    service_name="Memory %s",
    discovery_function=discover_huawei_switch_mem,
    check_function=check_huawei_switch_mem,
    check_ruleset_name="memory_percentage_used_multiitem",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
