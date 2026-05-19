#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<winperf_mem>>>
# 1440580801.44 4 3579545
# 24 5203433 counter
# 20 643575808 large_rawcount
# 22 291414016 large_rawcount
# 26 6212497408 large_rawcount
# 28 17614 counter
# 30 1012830 counter
# 32 3988745 counter
# 34 456907 counter
# 36 2011463 counter             -----> Pages Counter
# 818 2007095 counter
# 38 141612 counter
# 44 4368 counter
# 52 35241984 large_rawcount
# 54 6586368 large_rawcount
# 46 273 counter
# 56 41033 rawcount
# 60 33522 rawcount
# 674 3545 rawcount
# 814 114274304 large_rawcount
# 816 155688960 large_rawcount
# 62 35016704 large_rawcount
# 64 1003520 large_rawcount
# 66 131072 large_rawcount
# 68 2777088 large_rawcount
# 70 1777664 large_rawcount
# 72 77348864 large_rawcount
# 1402 71146 raw_fraction
# 1402 1516723 raw_base
# 1376 628492 large_rawcount
# 1378 613 large_rawcount


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


def parse_winperf_mem(string_table: StringTable) -> StringTable:
    return string_table


def discover_winperf_mem(section: StringTable) -> DiscoveryResult:
    if len(section) > 1:
        yield Service()


def check_winperf_mem(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    this_time = float(section[0][0])

    page_counter = 0
    for line in section:
        if line[0] == "36":
            page_counter = int(line[1])
            break

    pages_per_sec = get_rate(
        get_value_store(), "pages_count", this_time, page_counter, raise_overflow=True
    )
    state = State.OK
    if "pages_per_second" in params:
        warn, crit = params["pages_per_second"]
        if pages_per_sec >= crit:
            state = State.CRIT
        elif pages_per_sec >= warn:
            state = State.WARN

    yield Result(state=state, summary=f"Pages/s: {pages_per_sec:.0f}")
    yield Metric("mem_pages_rate", pages_per_sec)


agent_section_winperf_mem = AgentSection(
    name="winperf_mem",
    parse_function=parse_winperf_mem,
)


check_plugin_winperf_mem = CheckPlugin(
    name="winperf_mem",
    service_name="Memory Pages",
    discovery_function=discover_winperf_mem,
    check_function=check_winperf_mem,
    check_ruleset_name="mem_pages",
    check_default_parameters={},
)
