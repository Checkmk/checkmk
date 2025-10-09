#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from typing import TypedDict

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
)
from cmk.plugins.collection.agent_based.systemtime import Section


class Params(TypedDict):
    levels: tuple[int, int]


def discover_systemtime(section: Section) -> DiscoveryResult:
    yield Service()


def check_systemtime(params: Params, section: Section) -> CheckResult:
    if "foreign_systemtime" not in section:
        return

    systemtime = section["foreign_systemtime"]
    ourtime = section.get("our_systemtime") or time.time()
    offset = systemtime - ourtime

    warn, crit = params["levels"]
    yield from check_levels(
        offset,
        metric_name="offset",
        levels_upper=(warn, crit),
        levels_lower=(-warn, -crit),
        render_func=render.time_offset,
        label="Offset",
    )


check_plugin_systemtime = CheckPlugin(
    name="systemtime",
    service_name="System Time",
    discovery_function=discover_systemtime,
    check_function=check_systemtime,
    check_ruleset_name="systemtime",
    check_default_parameters=Params(levels=(30, 60)),
)
