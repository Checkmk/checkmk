#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"

# Author: Lars Michelsen <lm@mathias-kettner.de

# Example output of agent:
# <<<sylo>>>
#            7859            7859           10240
#
# Syntax of the hint file:
#
# +------------------------------------------+
# | in offset (Ascii, space padded, bytes)   |  16 Bytes
# +------------------------------------------+
# | out offset                               |  16 Bytes
# +------------------------------------------+
# | Size of sylo                             |  16 Bytes
# +------------------------------------------+
#
# The check_mk_agents add the mtime in front of the hint file contents

# 0: alive_report (max age of hint file in seconds)
# 1: warn fill level in percent
# 2: crit fill level in percent


import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, StringTable

check_info = {}


def discover_sylo(info):
    if len(info) > 0 and len(info[0]) == 4:
        return [(None, {})]
    return []


def check_sylo(item, params, info):
    if len(info) != 1:
        return (2, "No hint file (sylo probably never ran on this system)")

    if len(info[0]) == 4:
        msg = ""

        usage_warn_perc, usage_crit_perc = params["levels_usage_perc"]

        mtime = int(info[0][0])
        inOffset = int(info[0][1])
        outOffset = int(info[0][2])
        size = int(info[0][3])
        size_mb = size / (1024 * 1024.0)
        warn_mb = size_mb * usage_warn_perc / 100.0
        crit_mb = size_mb * usage_crit_perc / 100.0

        # CRIT: too old
        now = int(time.time())
        age = now - mtime
        if age > params["max_age_secs"]:
            status = 2
            return (2, "Sylo not running (Hintfile too old: last update %d secs ago)" % age)

        # Current fill state
        if inOffset == outOffset:
            bytesUsed = 0
        elif inOffset > outOffset:
            bytesUsed = inOffset - outOffset
        elif inOffset < outOffset:
            bytesUsed = size - outOffset + inOffset
        percUsed = float(bytesUsed) / size * 100
        used_mb = bytesUsed / (1024 * 1024.0)

        # Rates for input and output
        value_store = get_value_store()
        in_rate = get_rate(value_store, "sylo.in", mtime, inOffset, raise_overflow=True)
        out_rate = get_rate(value_store, "sylo.out", mtime, outOffset, raise_overflow=True)
        msg += f"Silo is filled {bytesUsed / (1024 * 1024.0):.1f}MB ({percUsed:.1f}%), in {in_rate:.1f} B/s, out {out_rate:.1f} B/s"

        status = 0
        if percUsed >= usage_crit_perc and status < 2:
            status = 2
        elif percUsed >= usage_warn_perc and status < 1:
            status = 1

        return (
            status,
            msg,
            [
                ("in", "%f" % in_rate),
                ("out", "%f" % out_rate),
                ("used", "%f" % used_mb, warn_mb, crit_mb, 0, size_mb),
            ],
        )

    return (3, "Invalid hint file contents: %s" % info)


def parse_sylo(string_table: StringTable) -> StringTable:
    return string_table


check_info["sylo"] = LegacyCheckDefinition(
    name="sylo",
    parse_function=parse_sylo,
    service_name="Sylo",
    discovery_function=discover_sylo,
    check_function=check_sylo,
    check_default_parameters={
        "max_age_secs": 70,
        "levels_usage_perc": (5.0, 25.0),
    },
)
