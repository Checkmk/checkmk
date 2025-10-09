# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)

Section = Mapping[str, float]


class Params(TypedDict):
    levels: tuple[int, int]


def parse_systemtime(string_table: StringTable) -> Section:
    """
    >>> parse_systemtime([['12345']])
    {'foreign_systemtime': 12345.0}
    >>> parse_systemtime([['12345.2', '567.3']])
    {'foreign_systemtime': 12345.2, 'our_systemtime': 567.3}
    >>> parse_systemtime([[]])
    {}
    """
    return {
        key: float(value)
        for key, value in zip(["foreign_systemtime", "our_systemtime"], string_table[0])
    }


agent_section_systemtime = AgentSection(
    name="systemtime",
    parse_function=parse_systemtime,
)


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
