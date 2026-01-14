#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<win_license>>>
#
# Name: Windows(R) 7, Enterprise edition
# Description: Windows Operating System - Windows(R) 7, TIMEBASED_EVAL channel
# Partial Product Key: JCDDG
# License Status: Initial grace period
# Time remaining: 11820 minute(s) (8 day(s))


import re

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render

TIME_LEFT_RE = re.compile(r"(\d+) minute")

check_info = {}


def parse_win_license(string_table):
    parsed: dict[str, str | int] = {}
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


def discover_win_license(parsed):
    if "License" in parsed:
        return [(None, {})]
    return []


def check_win_license(_item, params, parsed):
    if (sw_license := parsed.get("License")) is None:
        return

    message = "Software is %s" % sw_license

    license_state = 0 if sw_license in params["status"] else 2

    if license_state:
        message += " Required: " + " ".join(params["status"])

    yield license_state, message

    if (time_left := parsed.get("expiration_time")) is None:
        return

    if time_left < 0:
        yield 2, f"Licence expired {render.timespan(-time_left)} ago"
        return

    yield check_levels(
        time_left,
        None,
        (None, None) + params["expiration_time"],
        human_readable_func=render.timespan,
        infoname="Time until license expires",
    )


DEFAULT_PARAMETERS = {
    "status": ["Licensed", "Initial grace period"],
    "expiration_time": (14 * 24 * 60 * 60, 7 * 24 * 60 * 60),
}

check_info["win_license"] = LegacyCheckDefinition(
    name="win_license",
    parse_function=parse_win_license,
    service_name="Windows License",
    discovery_function=discover_win_license,
    check_function=check_win_license,
    check_ruleset_name="win_license",
    check_default_parameters=DEFAULT_PARAMETERS,
)
