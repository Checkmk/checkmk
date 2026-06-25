#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Service,
    StringTable,
)
from cmk.plugins.graylog.lib import deserialize_and_merge_json

# <<<graylog_jvm>>>
# {"jvm.memory.heap.init": 1073741824, "jvm.memory.heap.used": 357154208,
# "jvm.memory.heap.max": 1020067840, "jvm.memory.heap.committed": 1020067840,
# "jvm.memory.heap.usage": 0.35012789737592354}


@dataclass(frozen=True)
class GraylogJvmSection:
    used: int
    committed: int


class GraylogJvmParams(TypedDict):
    used: LevelsT[int]
    committed: LevelsT[int]


def parse_graylog_jvm(string_table: StringTable) -> GraylogJvmSection | None:
    match deserialize_and_merge_json(string_table):
        case {
            "jvm.memory.heap.used": int(heap_used),
            "jvm.memory.heap.committed": int(heap_committed),
        }:
            return GraylogJvmSection(
                used=heap_used,
                committed=heap_committed,
            )
        case _:
            return None


def discover_graylog_jvm(section: GraylogJvmSection) -> DiscoveryResult:
    yield Service()


def check_graylog_jvm(params: GraylogJvmParams, section: GraylogJvmSection) -> CheckResult:
    for key, value, metric_name, levels_upper in [
        ("used", section.used, "mem_heap", params["used"]),
        ("committed", section.committed, "mem_heap_committed", params["committed"]),
    ]:
        yield from check_levels(
            value=value,
            metric_name=metric_name,
            levels_upper=levels_upper,
            render_func=render.bytes,
            label=f"{key.title()} heap space",
        )


agent_section_graylog_jvm = AgentSection(
    name="graylog_jvm",
    parse_function=parse_graylog_jvm,
)


check_plugin_graylog_jvm = CheckPlugin(
    name="graylog_jvm",
    service_name="Graylog JVM",
    discovery_function=discover_graylog_jvm,
    check_function=check_graylog_jvm,
    check_ruleset_name="graylog_jvm",
    check_default_parameters={
        "used": ("no_levels", None),
        "committed": ("no_levels", None),
    },
)
