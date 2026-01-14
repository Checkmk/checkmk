#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_tsm_paths(info):
    return [(None, None)]


def check_tsm_paths(item, _no_params, info):
    count_pathes = len(info)
    error_paths = [x[1] for x in info if x[2] != "YES"]
    if len(error_paths) > 0:
        return 2, "Paths with errors: %s" % ", ".join(error_paths)
    return 0, " %d paths OK" % count_pathes


def parse_tsm_paths(string_table: StringTable) -> StringTable:
    return string_table


check_info["tsm_paths"] = LegacyCheckDefinition(
    name="tsm_paths",
    parse_function=parse_tsm_paths,
    service_name="TSM Paths",
    discovery_function=discover_tsm_paths,
    check_function=check_tsm_paths,
)
