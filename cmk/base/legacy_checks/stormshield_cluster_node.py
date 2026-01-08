#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import (
    check_levels,
    render,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.stormshield import DETECT_STORMSHIELD_CLUSTER

check_info = {}


online_mapping = {"1": "online", "0": "offline"}

active_mapping = {"1": "passive", "2": "active"}

forced_mapping = {"0": "not forced", "1": "forced"}


def inventory_stormshield_cluster_node(info):
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
    ) in info:
        yield index, {}


def check_stormshield_cluster_node(item, params, info):
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
    ) in info:
        if item == index:
            if online == "0":
                yield 2, "Member is %s" % online_mapping[online]
            else:
                yield 0, "Member is %s" % online_mapping[online]
            if statusforced == "1":
                yield (
                    1,
                    f"HA-State: {active_mapping[active]} ({forced_mapping[statusforced]})",
                )
            else:
                yield (
                    0,
                    f"HA-State: {active_mapping[active]} ({forced_mapping[statusforced]})",
                )
            yield from check_levels(
                float(quality),
                levels_lower=params["quality"],
                label="Quality",
                render_func=render.percent,
            )

            infotext = f"Model: {model}, Version: {version}, Role: {license_}, Priority: {priority}, Serial: {serial}"
            yield 0, infotext


def parse_stormshield_cluster_node(string_table: StringTable) -> StringTable:
    return string_table


check_info["stormshield_cluster_node"] = LegacyCheckDefinition(
    name="stormshield_cluster_node",
    parse_function=parse_stormshield_cluster_node,
    detect=DETECT_STORMSHIELD_CLUSTER,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.11.7.1",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
    ),
    service_name="HA Member %s",
    discovery_function=inventory_stormshield_cluster_node,
    check_function=check_stormshield_cluster_node,
    check_ruleset_name="stormshield_quality",
    check_default_parameters={
        "quality": ("fixed", (80.0, 50.0)),
    },
)
