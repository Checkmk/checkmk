#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Measures total allocated file handles.
# The output displays
#  - the number of allocated file handles
#  - the number of allocatedly used file handles (with the 2.4 kernel); or
#    the number of allocatedly unused file handles (with the 2.6 kernel)
#  - the maximum files handles that can be allocated
#    (can also be found in /proc/sys/fs/file-max)
# Example output of '/proc/sys/fs/file-nr':
# <<<filehandler>>>
# 9376        0        817805


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, StringTable

check_info = {}


def discover_filehandler(info):
    return [(None, {})]


def check_filehandler(_no_item, params, info):
    allocated, _used_or_unused, maximum = info[0]
    perc = float(allocated) / float(maximum) * 100.0

    # Add informational text about absolute values
    yield 0, f"({allocated} of {maximum} file handles)", []

    # Check levels on percentage
    yield check_levels(
        perc,
        "filehandler_perc",
        params["levels"],
        human_readable_func=render.percent,
        infoname="File handlers",
    )


def parse_filehandler(string_table: StringTable) -> StringTable:
    return string_table


check_info["filehandler"] = LegacyCheckDefinition(
    name="filehandler",
    parse_function=parse_filehandler,
    service_name="Filehandler",
    discovery_function=discover_filehandler,
    check_function=check_filehandler,
    check_ruleset_name="filehandler",
    check_default_parameters={"levels": (80.0, 90.0)},
)
