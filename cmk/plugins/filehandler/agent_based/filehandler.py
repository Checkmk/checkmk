#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)


def parse_filehandler(string_table: StringTable) -> StringTable:
    return string_table


def discover_filehandler(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_filehandler(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    allocated, _used_or_unused, maximum = section[0]
    perc = float(allocated) / float(maximum) * 100.0

    yield Result(state=State.OK, summary=f"({allocated} of {maximum} file handles)")

    warn, crit = params["levels"]
    yield from check_levels(
        perc,
        metric_name="filehandler_perc",
        levels_upper=("fixed", (warn, crit)),
        render_func=render.percent,
        label="File handlers",
    )


agent_section_filehandler = AgentSection(
    name="filehandler",
    parse_function=parse_filehandler,
)

check_plugin_filehandler = CheckPlugin(
    name="filehandler",
    service_name="Filehandler",
    discovery_function=discover_filehandler,
    check_function=check_filehandler,
    check_ruleset_name="filehandler",
    check_default_parameters={"levels": (80.0, 90.0)},
)
