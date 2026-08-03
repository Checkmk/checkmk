#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)


def discover_sylo(section: StringTable) -> DiscoveryResult:
    if len(section) > 0 and len(section[0]) == 4:
        yield Service()


def check_sylo(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if len(section) != 1:
        yield Result(
            state=State.CRIT, summary="No hint file (sylo probably never ran on this system)"
        )
        return

    if len(section[0]) == 4:
        usage_warn_perc, usage_crit_perc = params["levels_usage_perc"]

        mtime = int(section[0][0])
        inOffset = int(section[0][1])
        outOffset = int(section[0][2])
        size = int(section[0][3])
        size_mb = size / (1024 * 1024.0)
        warn_mb = size_mb * usage_warn_perc / 100.0
        crit_mb = size_mb * usage_crit_perc / 100.0

        # CRIT: too old
        now = int(time.time())
        age = now - mtime
        if age > params["max_age_secs"]:
            yield Result(
                state=State.CRIT,
                summary=f"Sylo not running (Hintfile too old: last update {age} secs ago)",
            )
            return

        # Current fill state
        if inOffset == outOffset:
            bytesUsed = 0
        elif inOffset > outOffset:
            bytesUsed = inOffset - outOffset
        else:
            bytesUsed = size - outOffset + inOffset
        percUsed = float(bytesUsed) / size * 100
        used_mb = bytesUsed / (1024 * 1024.0)

        # Rates for input and output
        value_store = get_value_store()
        in_rate = get_rate(value_store, "sylo.in", mtime, inOffset, raise_overflow=True)
        out_rate = get_rate(value_store, "sylo.out", mtime, outOffset, raise_overflow=True)
        msg = f"Silo is filled {used_mb:.1f}MB ({percUsed:.1f}%), in {in_rate:.1f} B/s, out {out_rate:.1f} B/s"

        if percUsed >= usage_crit_perc:
            state = State.CRIT
        elif percUsed >= usage_warn_perc:
            state = State.WARN
        else:
            state = State.OK

        yield Result(state=state, summary=msg)
        yield Metric("in", in_rate)
        yield Metric("out", out_rate)
        yield Metric("used", used_mb, levels=(warn_mb, crit_mb), boundaries=(0, size_mb))
        return

    yield Result(state=State.UNKNOWN, summary=f"Invalid hint file contents: {section}")


def parse_sylo(string_table: StringTable) -> StringTable:
    return string_table


agent_section_sylo = AgentSection(
    name="sylo",
    parse_function=parse_sylo,
)

check_plugin_sylo = CheckPlugin(
    name="sylo",
    service_name="Sylo",
    discovery_function=discover_sylo,
    check_function=check_sylo,
    check_default_parameters={
        "max_age_secs": 70,
        "levels_usage_perc": (5.0, 25.0),
    },
)
