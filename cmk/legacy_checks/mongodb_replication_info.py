#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mongodb_replication_info>>>
# <json>
# {
#   "tFirst": 1566891670,
#   "tLast": 1566891670,
#   "now": 1568796109,
#   "usedBytes": 9765922,
#   "logSizeBytes": 16830742272
# }


import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Any]


def parse_mongodb_replication_info(string_table: StringTable) -> Section:
    if string_table:
        parsed: Section = json.loads(str(string_table[0][0]))
        return parsed
    return {}


def discover_mongodb_replication_info(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_mongodb_replication_info(section: Section) -> CheckResult:
    oplog_size = (
        f"Oplog size: {_bytes_human_readable(section, 'usedBytes')} of "
        f"{_bytes_human_readable(section, 'logSizeBytes')} used"
    )

    try:
        timestamp_first_operation = section.get("tFirst", 0)
        timestamp_last_operation = section.get("tLast", 0)
        time_difference_sec = timestamp_last_operation - timestamp_first_operation
        time_diff = (
            f"Time difference: {render.timespan(time_difference_sec)} "
            f"between the first and last operation on oplog"
        )
    except TypeError:
        time_diff = "Time difference: n/a"

    yield Result(state=State.OK, summary=oplog_size)
    yield Result(state=State.OK, summary=time_diff)
    yield Result(state=State.OK, notice=_long_output(section))
    yield from _generate_performance_data(section)


def _generate_performance_data(section: Section) -> list[Metric]:
    log_size_bytes = _get_as_int(section, "logSizeBytes")
    used_bytes = _get_as_int(section, "usedBytes")
    timestamp_first_operation = _get_as_int(section, "tFirst")
    timestamp_last_operation = _get_as_int(section, "tLast")
    time_difference_sec = timestamp_last_operation - timestamp_first_operation

    return [
        Metric("mongodb_replication_info_log_size", log_size_bytes),
        Metric("mongodb_replication_info_used", used_bytes),
        Metric("mongodb_replication_info_time_diff", time_difference_sec),
    ]


def _long_output(section: Section) -> str:
    timestamp_first_operation = _timestamp_human_readable(section, "tFirst")
    timestamp_last_operation = _timestamp_human_readable(section, "tLast")
    timestamp_on_node = _timestamp_human_readable(section, "now")
    time_difference_sec = _calc_time_diff(section.get("tLast"), section.get("tFirst"))

    long_output = []
    long_output.append("Operations log (oplog):")
    long_output.append(
        f"- Total amount of space allocated: {_bytes_human_readable(section, 'logSizeBytes')}"
    )
    long_output.append(
        f"- Total amount of space currently used: {_bytes_human_readable(section, 'usedBytes')}"
    )
    long_output.append(f"- Timestamp for the first operation: {timestamp_first_operation}")
    long_output.append(f"- Timestamp for the last operation: {timestamp_last_operation}")
    long_output.append(f"- Difference between the first and last operation: {time_difference_sec}")
    long_output.append("")
    long_output.append(f"- Current time on host: {timestamp_on_node}")
    return "\n" + "\n".join(long_output)


def _bytes_human_readable(data: Mapping[str, Any], key: str) -> str:
    try:
        return render.bytes(int(data.get(key)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "n/a"


def _timestamp_human_readable(data: Mapping[str, Any], key: str) -> str:
    try:
        return render.datetime(int(data.get(key)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "n/a"


def _calc_time_diff(value1: int | None, value2: int | None) -> str:
    try:
        return render.timespan(value1 - value2)  # type: ignore[operator]
    except TypeError:
        return "n/a"


def _get_as_int(data: Mapping[str, Any], key: str) -> int:
    try:
        return int(data.get(key))  # type: ignore[arg-type]
    except (KeyError, ValueError, TypeError):
        return 0


agent_section_mongodb_replication_info = AgentSection(
    name="mongodb_replication_info",
    parse_function=parse_mongodb_replication_info,
)


check_plugin_mongodb_replication_info = CheckPlugin(
    name="mongodb_replication_info",
    service_name="MongoDB Replication Info",
    discovery_function=discover_mongodb_replication_info,
    check_function=check_mongodb_replication_info,
)
