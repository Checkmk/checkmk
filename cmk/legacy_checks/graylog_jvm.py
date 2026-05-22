#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
)
from cmk.plugins.graylog.lib import deserialize_and_merge_json

Section = dict[str, Any]

# <<<graylog_jvm>>>
# {"jvm.memory.heap.init": 1073741824, "jvm.memory.heap.used": 357154208,
# "jvm.memory.heap.max": 1020067840, "jvm.memory.heap.committed": 1020067840,
# "jvm.memory.heap.usage": 0.35012789737592354}


def discover_graylog_jvm(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_graylog_jvm(params: Mapping[str, Any], section: Section) -> CheckResult:
    if not section:
        return

    has_mem_data = False
    for key, metric_name in [
        ("used", "mem_heap"),
        ("committed", "mem_heap_committed"),
    ]:
        mem_data = section.get(f"jvm.memory.heap.{key}")
        if mem_data is None:
            continue

        has_mem_data = True
        yield from check_levels_v1(
            value=mem_data,
            metric_name=metric_name,
            levels_upper=params.get(key),
            render_func=render.bytes,
            label=f"{key.title()} heap space",
        )

    if not has_mem_data:
        yield Result(state=State.UNKNOWN, summary="No heap space data available")


agent_section_graylog_jvm = AgentSection(
    name="graylog_jvm",
    parse_function=deserialize_and_merge_json,
)


check_plugin_graylog_jvm = CheckPlugin(
    name="graylog_jvm",
    service_name="Graylog JVM",
    discovery_function=discover_graylog_jvm,
    check_function=check_graylog_jvm,
    check_ruleset_name="graylog_jvm",
    check_default_parameters={},
)
