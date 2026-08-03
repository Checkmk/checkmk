#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# Example output from agent:
# <<<logins>>>
# 3

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)

Section = int


def parse_logins(string_table: StringTable) -> Section | None:
    try:
        return int(string_table[0][0])
    except (IndexError, ValueError):
        return None


def discover_logins(section: Section) -> DiscoveryResult:
    yield Service()


def check_logins(params: Mapping[str, Any], section: Section) -> CheckResult:
    warn, crit = params["levels"]
    yield from check_levels(
        section,
        metric_name="logins",
        levels_upper=("fixed", (warn, crit)),
        render_func=lambda x: f"{int(x)}",
        label="On system",
    )


agent_section_logins = AgentSection(
    name="logins",
    parse_function=parse_logins,
)

check_plugin_logins = CheckPlugin(
    name="logins",
    service_name="Logins",
    discovery_function=discover_logins,
    check_function=check_logins,
    check_ruleset_name="logins",
    check_default_parameters={
        "levels": (20, 30),
    },
)
