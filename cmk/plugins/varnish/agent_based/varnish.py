#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from datetime import timedelta

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)

from .lib import parse_varnish, Section


def discover_varnish_uptime(section: Section) -> DiscoveryResult:
    if "uptime" in section:
        yield Service()


def check_varnish_uptime(section: Section) -> CheckResult:
    if (uptime := section.get("uptime")) is None:
        return
    try:
        yield from check_levels(
            uptime.value,
            metric_name="uptime",
            render_func=lambda x: str(timedelta(seconds=int(x))),
            label="Up since %s, uptime"
            % time.strftime("%c", time.localtime(time.time() - uptime.value)),
        )
    except OverflowError:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Could not handle uptime value {uptime.value!r}. "
            "Output of `varnishstats` seems to be faulty.",
        )


agent_section_varnish = AgentSection(
    name="varnish",
    parse_function=parse_varnish,
)


check_plugin_varnish = CheckPlugin(
    name="varnish",
    service_name="Varnish Uptime",
    discovery_function=discover_varnish_uptime,
    check_function=check_varnish_uptime,
)
