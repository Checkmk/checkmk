#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    exists,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

online_mapping = {"1": "online", "0": "offline"}

active_mapping = {"1": "passive", "2": "active"}

forced_mapping = {"0": "not forced", "1": "forced"}


def inventory_stormshield_cluster_node(section: StringTable) -> DiscoveryResult:
    for (
        index,
        _serial,
        _online,
        _model,
        _version,
        _license,
        _quality,
        _priority,
        _statusforced,
        _active,
        _uptime,
    ) in section:
        yield Service(item=index)


def check_stormshield_cluster_node(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for (
        index,
        serial,
        online,
        model,
        version,
        license_,
        quality,
        priority,
        statusforced,
        active,
        _uptime,
    ) in section:
        if item == index:
            if online == "0":
                yield Result(state=State.CRIT, summary="Member is %s" % online_mapping[online])
            else:
                yield Result(state=State.OK, summary="Member is %s" % online_mapping[online])
            if statusforced == "1":
                yield Result(
                    state=State.WARN,
                    summary=f"HA-State: {active_mapping[active]} ({forced_mapping[statusforced]})",
                )
            else:
                yield Result(
                    state=State.OK,
                    summary=f"HA-State: {active_mapping[active]} ({forced_mapping[statusforced]})",
                )
            yield from check_levels(
                float(quality),
                levels_lower=params["quality"],
                label="Quality",
                render_func=render.percent,
            )

            infotext = f"Model: {model}, Version: {version}, Role: {license_}, Priority: {priority}, Serial: {serial}"
            yield Result(state=State.OK, summary=infotext)


def parse_stormshield_cluster_node(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_stormshield_cluster_node = SimpleSNMPSection(
    name="stormshield_cluster_node",
    detect=all_of(
        any_of(
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.8"),
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11256.2.0"),
        ),
        exists(".1.3.6.1.4.1.11256.1.11.*"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.11.7.1",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
    ),
    parse_function=parse_stormshield_cluster_node,
)

check_plugin_stormshield_cluster_node = CheckPlugin(
    name="stormshield_cluster_node",
    service_name="HA Member %s",
    discovery_function=inventory_stormshield_cluster_node,
    check_function=check_stormshield_cluster_node,
    check_ruleset_name="stormshield_quality",
    check_default_parameters={
        "quality": ("fixed", (80.0, 50.0)),
    },
)
