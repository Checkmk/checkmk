#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)
from cmk.plugins.ddn_s2a.lib import parse_ddn_s2a_api_response

Section = Mapping[str, str]


def parse_ddn_s2a_uptime(string_table: StringTable) -> Section:
    return {key: value[0] for key, value in parse_ddn_s2a_api_response(string_table).items()}


def discover_ddn_s2a_uptime(section: Section) -> DiscoveryResult:
    yield Service()


def check_ddn_s2a_uptime(params: Mapping[str, Any], section: Section) -> CheckResult:
    uptime_years = int(section["uptime_years"])
    uptime_days = int(section["uptime_days"])
    uptime_hours = int(section["uptime_hours"])
    uptime_minutes = int(section["uptime_minutes"])

    uptime_sec = 60 * (
        uptime_minutes + 60 * (uptime_hours + 24 * (uptime_days + 365 * uptime_years))
    )

    yield from check_levels(
        uptime_sec,
        "uptime",
        params.get("max", (None, None)) + params.get("min", (None, None)),
        human_readable_func=lambda x: timedelta(seconds=int(x)),
        infoname="Up since %s, uptime"
        % time.strftime("%c", time.localtime(time.time() - uptime_sec)),
    )


agent_section_ddn_s2a_uptime = AgentSection(
    name="ddn_s2a_uptime",
    parse_function=parse_ddn_s2a_uptime,
)


check_plugin_ddn_s2a_uptime = CheckPlugin(
    name="ddn_s2a_uptime",
    # We don't use "Uptime" as a service name here, because this value is
    # different from the uptime value supplied via SNMP.
    service_name="DDN S2A Power-On Time",
    discovery_function=discover_ddn_s2a_uptime,
    check_function=check_ddn_s2a_uptime,
    check_ruleset_name="uptime",
    check_default_parameters={},
)
