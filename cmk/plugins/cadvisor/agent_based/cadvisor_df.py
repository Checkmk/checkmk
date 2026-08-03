#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
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

Section = Mapping[str, Any]


def parse_cadvisor_df(string_table: StringTable) -> Section:
    diskstat_info = json.loads(string_table[0][0])
    parsed: dict[str, float] = {}
    for diskstat_name, diskstat_entries in diskstat_info.items():
        if len(diskstat_entries) != 1:
            continue
        try:
            parsed[diskstat_name] = float(diskstat_entries[0]["value"])
        except KeyError:
            continue
    return parsed


def discover_cadvisor_df(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_cadvisor_df(params: Mapping[str, Any], section: Section) -> CheckResult:
    size_mb = section["df_size"] / 1024**2
    avail_mb = size_mb - (section["df_used"] / 1024**2)
    inodes_total = section["inodes_total"]
    inodes_free = section["inodes_free"]
    yield from df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint="filesystem",
        filesystem_size=size_mb,
        free_space=avail_mb,
        reserved_space=0,
        inodes_total=inodes_total,
        inodes_avail=inodes_free,
        params=params,
    )


agent_section_cadvisor_df = AgentSection(
    name="cadvisor_df",
    parse_function=parse_cadvisor_df,
)

check_plugin_cadvisor_df = CheckPlugin(
    name="cadvisor_df",
    service_name="Filesystem",
    discovery_function=discover_cadvisor_df,
    check_function=check_cadvisor_df,
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
