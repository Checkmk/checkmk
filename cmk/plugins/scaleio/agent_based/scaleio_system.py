#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.scaleio.lib import parse_scaleio, ScaleioSection

# <<<scaleio_system:sep(9)>>>
# SYSTEM 5914d6b47d479d5a:
#        ID                                                 5914d6b47d479d5a
#        NAME                                               N/A
#        CAPACITY_ALERT_HIGH_THRESHOLD                      80%
#        CAPACITY_ALERT_CRITICAL_THRESHOLD                  90%
#        MAX_CAPACITY_IN_KB                                 65.5 TB (67059 GB)
#        UNUSED_CAPACITY_IN_KB                              17.2 TB (17635 GB)


def parse_scaleio_system(string_table: StringTable) -> ScaleioSection:
    return parse_scaleio(string_table, "SYSTEM")


def discover_scaleio_system(section: ScaleioSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_scaleio_system(
    item: str, params: Mapping[str, Any], section: ScaleioSection
) -> CheckResult:
    if not (data := section.get(item)):
        return

    effective_params: dict[str, Any] = {
        "levels": (
            float(data["CAPACITY_ALERT_HIGH_THRESHOLD"][0].strip("%")),
            float(data["CAPACITY_ALERT_CRITICAL_THRESHOLD"][0].strip("%")),
        ),
        **params,
    }
    total = int(data["MAX_CAPACITY_IN_KB"][2].strip("(")) * 1024
    free = int(data["UNUSED_CAPACITY_IN_KB"][2].strip("(")) * 1024

    yield from df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint=item,
        filesystem_size=float(total),
        free_space=float(free),
        reserved_space=0.0,
        inodes_avail=None,
        inodes_total=None,
        params=effective_params,
    )


agent_section_scaleio_system = AgentSection(
    name="scaleio_system",
    parse_function=parse_scaleio_system,
)


check_plugin_scaleio_system = CheckPlugin(
    name="scaleio_system",
    service_name="ScaleIO System %s",
    discovery_function=discover_scaleio_system,
    check_function=check_scaleio_system,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
