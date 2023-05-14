#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import (
    check_levels,
    discover_single,
    get_bytes_human_readable,
    LegacyCheckDefinition,
)
from cmk.base.check_legacy_includes.graylog import parse_graylog_agent_data
from cmk.base.config import check_info

# <<<graylog_jvm>>>
# {"jvm.memory.heap.init": 1073741824, "jvm.memory.heap.used": 357154208,
# "jvm.memory.heap.max": 1020067840, "jvm.memory.heap.committed": 1020067840,
# "jvm.memory.heap.usage": 0.35012789737592354}


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
            human_readable_func=get_bytes_human_readable,
            infoname="%s heap space" % key.title(),
        )
    if not has_mem_data:
        yield 3, "No heap space data available"


check_info["graylog_jvm"] = LegacyCheckDefinition(
    parse_function=parse_graylog_agent_data,
    check_function=check_graylog_jvm,
    discovery_function=discover_single,
    service_name="Graylog JVM",
    check_ruleset_name="graylog_jvm",
)
