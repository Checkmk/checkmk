#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# <<<symantec_av_updates>>>
# 15.05.2015 rev. 1

# <<<symantec_av_updates>>>
# 05/15/2015 rev. 1

# <<<symantec_av_updates>>>
# 09/18/15 rev. 1


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)


def discover_symantec_av_updates(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_symantec_av_updates(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    last_text = section[0][0]
    if "/" in last_text:
        if len(last_text) == 10:
            last_broken = time.strptime(last_text, "%m/%d/%Y")
        else:
            last_broken = time.strptime(last_text, "%m/%d/%y")
    else:
        last_broken = time.strptime(last_text, "%d.%m.%Y")

    last_timestamp = time.mktime(last_broken)
    age = time.time() - last_timestamp

    warn, crit = params["levels"]
    yield from check_levels(
        age,
        levels_upper=("fixed", (warn, crit)),
        render_func=render.timespan,
        label="Time since last update",
    )


def parse_symantec_av_updates(string_table: StringTable) -> StringTable:
    return string_table


agent_section_symantec_av_updates = AgentSection(
    name="symantec_av_updates",
    parse_function=parse_symantec_av_updates,
)

check_plugin_symantec_av_updates = CheckPlugin(
    name="symantec_av_updates",
    service_name="AV Update Status",
    discovery_function=discover_symantec_av_updates,
    check_function=check_symantec_av_updates,
    check_ruleset_name="antivir_update_age",
    check_default_parameters={
        "levels": (3600 * 24 * 3, 3600 * 24 * 4),
    },
)
