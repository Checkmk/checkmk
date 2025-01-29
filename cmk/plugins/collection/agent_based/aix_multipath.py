#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# <<<aix_multipath>>>
# <<<aix_multipath>>>
# hdisk0 vscsi0 Available Enabled
# hdisk1 vscsi0 Available Enabled
# hdisk2 vscsi0 Available Enabled


# mypy: disable-error-code="var-annotated"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def inventory_aix_multipath(section: StringTable) -> DiscoveryResult:
    disks = {}
    for disk, _controller, _status in section:
        # filtering here to only see disks. there are other multipath devices,
        # too, but those have incomplete status => false positives
        if disk.startswith("hdisk"):
            disks[disk] = disks.get(disk, 0) + 1
    yield from [Service(item=disk, parameters={"paths": p}) for disk, p in disks.items()]


def check_aix_multipath(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    path_count = 0
    state_count = 0

    # Collecting all paths and there states
    for disk, _controller, status in section:
        if disk == item:
            path_count += 1
            if status != "Enabled":
                state_count += 1

    # How many Paths are not enabled
    if state_count != 0:
        yield Result(
            state=State.WARN if (100.0 / path_count * state_count) < 50 else State.CRIT,
            summary=f"Paths not enabled: {state_count}",
        )

    # Are some paths missing?
    path_message = f"Paths in total: {path_count}"
    if path_count != params["paths"]:
        yield Result(state=State.WARN, summary=path_message + f" (should be: {params['paths']})")
    else:
        yield Result(state=State.OK, summary=path_message)


def parse_aix_multipath(string_table: StringTable) -> StringTable:
    return string_table


agent_section_aix_multipath = AgentSection(
    name="aix_multipath",
    parse_function=parse_aix_multipath,
)


check_plugin_aix_multipath = CheckPlugin(
    name="aix_multipath",
    service_name="Multipath %s",
    discovery_function=inventory_aix_multipath,
    check_function=check_aix_multipath,
    check_default_parameters={},
)
