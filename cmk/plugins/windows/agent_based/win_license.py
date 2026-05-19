#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<win_license>>>
#
# Name: Windows(R) 7, Enterprise edition
# Description: Windows Operating System - Windows(R) 7, TIMEBASED_EVAL channel
# Partial Product Key: JCDDG
# License Status: Initial grace period
# Time remaining: 11820 minute(s) (8 day(s))


import re
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

TIME_LEFT_RE = re.compile(r"(\d+) minute")

Section = dict[str, str | int]


def parse_win_license(string_table: StringTable) -> Section:
    parsed: Section = {}
    for line in string_table:
        if len(line) == 0:
            continue

        if line[0] == "License":
            parsed["License"] = " ".join(line[2:])

        # Depending on Windows version this variable reads
        # Time remaining or Volume activation expiration or is not present
        if line[0] in ["Time", "Timebased", "Volume"]:
            expiration = " ".join(line).split(":")[1].strip()
            parsed["expiration"] = expiration
            if (search := TIME_LEFT_RE.search(expiration)) is None:
                raise ValueError(expiration)
            time_left = int(search.group(1)) * 60
            parsed["expiration_time"] = time_left
    return parsed


def discover_win_license(section: Section) -> DiscoveryResult:
    if "License" in section:
        yield Service()


def check_win_license(params: Mapping[str, Any], section: Section) -> CheckResult:
    if (sw_license := section.get("License")) is None:
        return

    message = f"Software is {sw_license}"
    license_ok = sw_license in params["status"]

    if not license_ok:
        message += " Required: " + " ".join(params["status"])

    yield Result(state=State.OK if license_ok else State.CRIT, summary=message)

    if (time_left := section.get("expiration_time")) is None:
        return
    assert isinstance(time_left, int)

    if time_left < 0:
        yield Result(state=State.CRIT, summary=f"Licence expired {render.timespan(-time_left)} ago")
        return

    yield from check_levels_v1(
        time_left,
        levels_lower=params["expiration_time"],
        render_func=render.timespan,
        label="Time until license expires",
    )


DEFAULT_PARAMETERS = {
    "status": ["Licensed", "Initial grace period"],
    "expiration_time": (14 * 24 * 60 * 60, 7 * 24 * 60 * 60),
}


agent_section_win_license = AgentSection(
    name="win_license",
    parse_function=parse_win_license,
)


check_plugin_win_license = CheckPlugin(
    name="win_license",
    service_name="Windows License",
    discovery_function=discover_win_license,
    check_function=check_win_license,
    check_ruleset_name="win_license",
    check_default_parameters=DEFAULT_PARAMETERS,
)
