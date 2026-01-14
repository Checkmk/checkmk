#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<hyperv_checkpoints>>>
# Has_Checkpoints
# f5689086-243b-4dfe-9775-571ef6be8a1b 2063
# c85ae17b-1a6c-4a34-949a-a1b9385ef67a 2040


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, StringTable

check_info = {}


def discover_hyperv_checkpoints(info):
    return [(None, {})]


def check_hyperv_checkpoints(item, params, info):
    snapshots = []
    for line in info:
        if len(line) != 2:
            continue
        snapshots.append((line[0], int(line[1])))

    yield 0, "%s checkpoints" % len(snapshots)

    if not snapshots:
        return

    # We assume that the last snapshot is the last line
    # of the agent output
    for title, key, snapshot in [
        ("Oldest", "age_oldest", max(snapshots, key=lambda x: x[1])),
        ("Last", "age", snapshots[-1]),
    ]:
        name, age = snapshot
        yield check_levels(
            age,
            key,
            params.get(key),
            human_readable_func=render.timespan,
            infoname=f"{title} ({name})",
        )


def parse_hyperv_checkpoints(string_table: StringTable) -> StringTable:
    return string_table


check_info["hyperv_checkpoints"] = LegacyCheckDefinition(
    name="hyperv_checkpoints",
    parse_function=parse_hyperv_checkpoints,
    service_name="HyperV Checkpoints",
    discovery_function=discover_hyperv_checkpoints,
    check_function=check_hyperv_checkpoints,
    check_ruleset_name="vm_snapshots",
)
