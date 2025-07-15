#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Iterable, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

check_info = {}

Section = Mapping[str, Any]


def parse_cadvisor_df(string_table):
    diskstat_info = json.loads(string_table[0][0])
    parsed = {}
    for diskstat_name, diskstat_entries in diskstat_info.items():
        if len(diskstat_entries) != 1:
            continue
        try:
            parsed[diskstat_name] = float(diskstat_entries[0]["value"])
        except KeyError:
            continue
    return parsed


def discover_cadvisor_df(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_cadvisor_df(item, _params, parsed):
    size_mb = parsed["df_size"] / 1024**2
    avail_mb = size_mb - (parsed["df_used"] / 1024**2)
    reserved_mb = 0
    inodes_total = parsed["inodes_total"]
    inodes_free = parsed["inodes_free"]
    return df_check_filesystem_single(
        item, size_mb, avail_mb, reserved_mb, inodes_total, inodes_free, FILESYSTEM_DEFAULT_PARAMS
    )


check_info["cadvisor_df"] = LegacyCheckDefinition(
    name="cadvisor_df",
    parse_function=parse_cadvisor_df,
    service_name="Filesystem",
    discovery_function=discover_cadvisor_df,
    check_function=check_cadvisor_df,
)
