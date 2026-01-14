#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Agent output:
# <<<windows_multipath>>>
# 4
# (yes, thats all)


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_windows_multipath(info):
    try:
        num_active = int(info[0][0])
    except (ValueError, IndexError):
        return

    if num_active > 0:
        yield None, {"active_paths": num_active}


def check_windows_multipath(item, params, info):
    num_active = int(info[0][0])

    yield 0, "Paths active: %s" % (num_active)

    levels = params["active_paths"]
    if isinstance(levels, tuple):
        num_paths, warn, crit = levels
        warn_num = (warn / 100.0) * num_paths
        crit_num = (crit / 100.0) * num_paths
        if num_active < crit_num:
            state = 2
        elif num_active < warn_num:
            state = 1
        else:
            state = 0

        if state > 0:
            yield state, "(warn/crit below %d/%d)" % (warn_num, crit_num)
    else:
        yield 0, "Expected paths: %s" % levels
        if num_active < levels:
            yield 2, "(crit below %d)" % levels
        elif num_active > levels:
            yield 1, "(warn at %d)" % levels


def parse_windows_multipath(string_table: StringTable) -> StringTable:
    return string_table


check_info["windows_multipath"] = LegacyCheckDefinition(
    name="windows_multipath",
    parse_function=parse_windows_multipath,
    service_name="Multipath",
    discovery_function=discover_windows_multipath,
    check_function=check_windows_multipath,
    check_ruleset_name="windows_multipath",
    check_default_parameters={"active_paths": 4},
)
