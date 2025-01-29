#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.plugins.lib.graylog import deserialize_and_merge_json, GraylogSection

check_info = {}

# <<<graylog_jvm>>>
# {"jvm.memory.heap.init": 1073741824, "jvm.memory.heap.used": 357154208,
# "jvm.memory.heap.max": 1020067840, "jvm.memory.heap.committed": 1020067840,
# "jvm.memory.heap.usage": 0.35012789737592354}


def discover_graylog_jvm(section: GraylogSection) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_graylog_jvm(_no_item, params, parsed):
    if parsed is None:
        return

    has_mem_data = False
    for key, metric_name in [
        ("used", "mem_heap"),
        ("committed", "mem_heap_committed"),
    ]:
        mem_data = parsed.get("jvm.memory.heap.%s" % key)
        if mem_data is None:
            continue

        has_mem_data = True
        yield check_levels(
            mem_data,
            metric_name,
            params.get(key),
            human_readable_func=render.bytes,
            infoname="%s heap space" % key.title(),
        )
    if not has_mem_data:
        yield 3, "No heap space data available"


check_info["graylog_jvm"] = LegacyCheckDefinition(
    name="graylog_jvm",
    parse_function=deserialize_and_merge_json,
    service_name="Graylog JVM",
    discovery_function=discover_graylog_jvm,
    check_function=check_graylog_jvm,
    check_ruleset_name="graylog_jvm",
)
