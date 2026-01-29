#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import json
from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import (
    LegacyCheckDefinition,
    LegacyCheckResult,
)
from cmk.base.check_legacy_includes.mem import check_memory_element

check_info = {}

Section = Mapping[str, float]


def parse_cadvisor_memory(string_table: list[list[str]]) -> Section:
    memory_info = json.loads(string_table[0][0])
    parsed = {}
    for memory_name, memory_entries in memory_info.items():
        if len(memory_entries) != 1:
            continue
        try:
            parsed[memory_name] = float(memory_entries[0]["value"])
        except KeyError:
            continue
    return parsed


def _output_single_memory_stat(
    memory_value: float, output_text: str, metric_name: str | None = None
) -> tuple[int, str, list[tuple[str, float, int | float | None, int | float | None]]]:
    infotext = output_text % (memory_value / 1024)
    perfdata: list[tuple[str, float, int | float | None, int | float | None]]
    if metric_name:
        perfdata = [(metric_name, memory_value, None, None)]
    else:
        perfdata = []
    return 0, infotext, perfdata


def discover_cadvisor_memory(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_cadvisor_memory(_item: object, _params: object, parsed: Section) -> LegacyCheckResult:
    # Checking for Container
    if "memory_usage_container" in parsed:
        memory_used = parsed["memory_usage_container"]
        memory_total = parsed["memory_usage_pod"]
        infotext_extra = " (Parent pod memory usage)"

    # Checking for Pod
    else:
        memory_used = parsed["memory_usage_pod"]
        if parsed.get("memory_limit", 0):
            memory_total = parsed["memory_limit"]
            infotext_extra = ""
        else:
            memory_total = parsed["memory_machine"]
            infotext_extra = " (Available Machine Memory)"
    status, infotext, perfdata = check_memory_element(
        "Usage", memory_used, memory_total, None, metric_name="mem_used"
    )
    infotext += infotext_extra
    yield status, infotext, perfdata

    # the cAdvisor does not provide available (total) memory of the following
    yield _output_single_memory_stat(parsed["memory_rss"], "Resident size: %s kB")

    yield _output_single_memory_stat(parsed["memory_cache"], "Cache: %s kB", "mem_lnx_cached")

    yield _output_single_memory_stat(parsed["memory_swap"], "Swap: %s kB", "swap_used")


check_info["cadvisor_memory"] = LegacyCheckDefinition(
    name="cadvisor_memory",
    parse_function=parse_cadvisor_memory,
    service_name="Memory",
    discovery_function=discover_cadvisor_memory,
    check_function=check_cadvisor_memory,
)
