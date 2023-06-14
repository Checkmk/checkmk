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


from cmk.base.check_api import get_age_human_readable, LegacyCheckDefinition, regex
from cmk.base.config import check_info


def parse_win_license(info):
    parsed: dict[str, str | int] = {}
    for line in info:
        if len(line) == 0:
            continue

        if line[0] == "License":
            parsed["License"] = " ".join(line[2:])

        # Depending on Windows version this variable reads
        # Time remaining or Volume activation expiration or is not present
        if line[0] in ["Time", "Volume"]:
            expiration = " ".join(line).split(":")[1].strip()
            parsed["expiration"] = expiration
            time_left_re = regex(r"(\d+) minute")
            if (search := time_left_re.search(expiration)) is None:
                raise ValueError(expiration)
            time_left = int(search.group(1)) * 60
            parsed["expiration_time"] = time_left
    return parsed


def inventory_win_license(parsed):
    if "License" in parsed:
        return [(None, {})]
    return []


def check_win_license(_item, params, parsed):
    sw_license = parsed.get("License", None)

    if not sw_license:
        return

    message = "Software is %s" % sw_license

    license_state = 0 if sw_license in params["status"] else 2

    if license_state:
        message += " Required: " + " ".join(params["status"])

    yield license_state, message

    time_left = parsed.get("expiration_time", None)

    if not time_left:
        return

    time_message = "License will expire in %s" % get_age_human_readable(time_left)

    warn, crit = params["expiration_time"]

    time_state = 0

    if time_left < crit:
        time_state = 2
    elif time_left < warn:
        time_state = 1

    if time_state:
        time_message += " (warn/crit at %s/%s)" % tuple(map(get_age_human_readable, (warn, crit)))

    yield time_state, time_message


check_info["win_license"] = LegacyCheckDefinition(
    service_name="Windows License",
    parse_function=parse_win_license,
    discovery_function=inventory_win_license,
    check_function=check_win_license,
    check_ruleset_name="win_license",
    check_default_parameters={
        "status": ["Licensed", "Initial grace period"],
        "expiration_time": (14 * 24 * 60 * 60, 7 * 24 * 60 * 60),
    },
)
