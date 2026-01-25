#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


import json
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import timedelta
from typing import Any

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
)
from cmk.agent_based.v2 import render, StringTable
from cmk.base.check_legacy_includes.mem import check_memory_element

check_info = {}

# <<<rabbitmq_nodes>>>
# {"fd_total": 1098576, "sockets_total": 973629, "mem_limit": 6808874700,
# "mem_alarm": false, "disk_free_limit": 70000000, "disk_free_alarm": false,
# "proc_total": 1088576, "run_queue": 1, "name": "rabbit@my-rabbit", "type":
# "disc", "running": true, "mem_key": 108834752, "fd_key": 35,
# "sockets_key": 0, "proc_key": 429, "gc_num": 70927, "gc_bytes_reclaimed":
# 1586846120, "io_file_handle_open_attempt_count": 13, "node_links":
# []}
# {"fd_total": 1048576, "sockets_total": 943629, "mem_limit": 6608874700,
# "mem_alarm": false, "disk_free_limit": 50000000, "disk_free_alarm": false,
# "proc_total": 1048576, "run_queue": 1, "name": "rabbit2@my-rabbit", "type":
# "disc", "running": true, "mem_key": 101834752, "fd_key": 33,
# "sockets_key": 0, "proc_key": 426, "gc_num": 70827, "gc_bytes_reclaimed":
# 1556846120, "io_file_handle_open_attempt_count": 11, "node_links":
# []}

_ItemData = dict

Section = Mapping[str, _ItemData]


def discover_key(key: str) -> Callable[[Section], Iterable[tuple[str, dict]]]:
    def _discover_bound_key(section: Section) -> Iterable[tuple[str, dict]]:
        yield from ((item, {}) for item, data in section.items() if key in data)

    return _discover_bound_key


def parse_rabbitmq_nodes(string_table: StringTable) -> Section:
    parsed: dict[str, _ItemData] = {}

    for nodes in string_table:
        for node_json in nodes:
            node = json.loads(node_json)

            node_name = node.get("name")
            if node_name is not None:
                fd_stats = {
                    "fd_used": node.get("fd_used"),
                    "fd_total": node.get("fd_total"),
                    "fd_open": node.get("io_file_handle_open_attempt_count"),
                    "fd_open_rate": node.get("io_file_handle_open_attempt_count_details", {}).get(
                        "rate"
                    ),
                }

                sockets = {
                    "sockets_used": node.get("sockets_used"),
                    "sockets_total": node.get("sockets_total"),
                }

                proc = {
                    "proc_used": node.get("proc_used"),
                    "proc_total": node.get("proc_total"),
                }

                mem = {
                    "mem_used": node.get("mem_used"),
                    "mem_limit": node.get("mem_limit"),
                }

                gc_stats = {
                    "gc_num": node.get("gc_num"),
                    "gc_num_rate": node.get("gc_num_details", {}).get("rate"),
                    "gc_bytes_reclaimed": node.get("gc_bytes_reclaimed"),
                    "gc_bytes_reclaimed_rate": node.get("gc_bytes_reclaimed_details", {}).get(
                        "rate"
                    ),
                    "run_queue": node.get("run_queue"),
                }

                uptime = {
                    "uptime": None if (raw := node.get("uptime")) is None else float(raw) / 1000.0
                }

                parsed.setdefault(
                    node_name,
                    {
                        "type": node.get("type"),
                        "state": node.get("running"),
                        "disk_free_alarm": node.get("disk_free_alarm"),
                        "mem_alarm": node.get("mem_alarm"),
                        "fd": fd_stats,
                        "sockets": sockets,
                        "proc": proc,
                        "mem": mem,
                        "gc": gc_stats,
                        "uptime": uptime,
                    },
                )

    return parsed


def discover_rabbitmq_nodes(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((item, {}) for item in section)


def check_rabbitmq_nodes(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    node_type = data.get("type")
    if node_type is not None:
        yield 0, "Type: %s" % node_type.title()

    node_state = data.get("state")
    if node_state is not None:
        state = 0
        if not node_state:
            state = params.get("state")
        yield (
            state,
            "Is running: %s" % str(node_state).replace("True", "yes").replace("False", "no"),
        )

    for alarm_key, alarm_infotext in [
        ("disk_free_alarm", "Disk alarm in effect"),
        ("mem_alarm", "Memory alarm in effect"),
    ]:
        alarm_value = data.get(alarm_key)
        if alarm_value is None:
            continue

        alarm_state = 0
        if alarm_value:
            alarm_state = params.get(alarm_key)

            yield (
                alarm_state,
                "{}: {}".format(
                    alarm_infotext,
                    str(alarm_value).replace("True", "yes").replace("False", "no"),
                ),
            )


check_info["rabbitmq_nodes"] = LegacyCheckDefinition(
    name="rabbitmq_nodes",
    parse_function=parse_rabbitmq_nodes,
    service_name="RabbitMQ Node %s",
    discovery_function=discover_rabbitmq_nodes,
    check_function=check_rabbitmq_nodes,
    check_ruleset_name="rabbitmq_nodes",
    check_default_parameters={
        "state": 2,
        "disk_free_alarm": 2,
        "mem_alarm": 2,
    },
)


def check_rabbitmq_nodes_filedesc(item, params, parsed):
    fd_data = parsed.get(item, {}).get("fd")
    if not fd_data:
        return

    value = fd_data.get("fd_used")
    if value is None:
        return

    total = fd_data.get("fd_total")
    if total is None:
        return

    yield _handle_output(params, value, total, "File descriptors used", "open_file_descriptors")

    open_fd = fd_data.get("fd_open")
    if open_fd is not None:
        levels_upper = params.get("fd_open_upper", (None, None))

        yield check_levels(
            open_fd,
            "file_descriptors_open_attempts",
            levels_upper,
            human_readable_func=int,
            infoname="File descriptor open attempts",
        )

    open_fd_rate = fd_data.get("fd_open_rate")
    if open_fd_rate is not None:
        levels_upper = params.get("fd_open_rate_upper", (None, None))
        levels_lower = params.get("fd_open_rate_lower", (None, None))

        yield check_levels(
            open_fd_rate,
            "file_descriptors_open_attempts_rate",
            levels_upper + levels_lower,
            human_readable_func=lambda x: f"{float(x):.2f}/s",
            infoname="Rate",
        )


check_info["rabbitmq_nodes.filedesc"] = LegacyCheckDefinition(
    name="rabbitmq_nodes_filedesc",
    service_name="RabbitMQ Node %s Filedesc",
    sections=["rabbitmq_nodes"],
    discovery_function=discover_key("fd"),
    check_function=check_rabbitmq_nodes_filedesc,
    check_ruleset_name="rabbitmq_nodes_filedesc",
)


def check_rabbitmq_nodes_mem(item, params, parsed):
    mem_data = parsed.get(item, {}).get("mem")
    if not mem_data:
        return

    mem_used = mem_data.get("mem_used")
    if mem_used is None:
        return

    mem_mark = mem_data.get("mem_limit")
    if mem_mark is None:
        return

    levels = params.get("levels")
    yield check_memory_element(
        "Memory used",
        mem_used,
        mem_mark,
        (
            "abs_used" if isinstance(levels, tuple) and isinstance(levels[0], int) else "perc_used",
            levels,
        ),
        label_total="High watermark",
        metric_name="mem_used",
    )


check_info["rabbitmq_nodes.mem"] = LegacyCheckDefinition(
    name="rabbitmq_nodes_mem",
    service_name="RabbitMQ Node %s Memory",
    sections=["rabbitmq_nodes"],
    discovery_function=discover_key("mem"),
    check_function=check_rabbitmq_nodes_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters={"levels": None},
)

_UNITS_NODES_GC = {"gc_num_rate": "1/s"}


_METRIC_SPECS: Sequence[tuple[str, str, Callable, str]] = [
    ("gc_num", "GC runs", int, "gc_runs"),
    ("gc_num_rate", "Rate", float, "gc_runs_rate"),
    ("gc_bytes_reclaimed", "Bytes reclaimed by GC", render.bytes, "gc_bytes"),
    ("gc_bytes_reclaimed_rate", "Rate", render.iobandwidth, "gc_bytes_rate"),
    ("run_queue", "Runtime run queue", int, "runtime_run_queue"),
]


def _get_levels(params, key):
    if key not in params:
        return None, None

    level_type, levels = params[key]
    if level_type == "no_levels":
        return None, None
    return levels


def check_rabbitmq_nodes_gc(item, params, parsed):
    gc_data = parsed.get(item, {}).get("gc")
    if not gc_data:
        return

    for key, infotext, hr_func, perf_key in _METRIC_SPECS:
        value = gc_data.get(key)
        if value is None:
            continue

        levels_upper = _get_levels(params, f"{key}_upper")
        levels_lower = _get_levels(params, f"{key}_lower")

        yield check_levels(
            value,
            perf_key,
            levels_upper + levels_lower,
            human_readable_func=lambda x, hr=hr_func, u=_UNITS_NODES_GC.get(key, ""): f"{hr(x)}{u}",
            infoname=infotext,
        )


def check_rabbitmq_nodes_uptime(
    item: str, params: Mapping[str, Any], section: Section
) -> LegacyCheckResult:
    try:
        if (uptime := section[item]["uptime"]["uptime"]) is None:
            return
    except KeyError:
        return

    params = params.get("max", (None, None)) + params.get("min", (None, None))
    yield 0, f"Up since {time.strftime('%c', time.localtime(time.time() - uptime))}", []
    yield check_levels(
        uptime,
        "uptime",
        params,
        human_readable_func=lambda x: timedelta(seconds=int(x)),
        infoname="Uptime",
    )


check_info["rabbitmq_nodes.uptime"] = LegacyCheckDefinition(
    name="rabbitmq_nodes_uptime",
    service_name="RabbitMQ Node %s Uptime",
    sections=["rabbitmq_nodes"],
    discovery_function=discover_key("uptime"),
    check_function=check_rabbitmq_nodes_uptime,
    check_ruleset_name="rabbitmq_nodes_uptime",
)


def _handle_output(params, value, total, info_text, perf_key):
    levels = params.get("levels")
    if levels is None:
        warn, crit = (None, None)
    else:
        warn, crit = levels[1]

    perc_value = 100.0 * value / total

    if isinstance(warn, float) and isinstance(crit, float):
        value_check = perc_value
        warn_abs: int | None = int((warn / 100.0) * total)
        crit_abs: int | None = int((crit / 100.0) * total)
        level_msg = f" (warn/crit at {render.percent(warn)}/{render.percent(crit)})"
    else:
        value_check = value
        warn_abs = warn
        crit_abs = crit
        level_msg = f" (warn/crit at {warn}/{crit})"

    state, _info, _perf = check_levels(
        value_check,
        None,
        (warn, crit),
    )

    infotext = f"{info_text}: {value} of {total}, {render.percent(perc_value)}"

    if state:
        infotext += level_msg

    # construct perfdata for absolut values even perc levels are set
    return state, infotext, [(perf_key, value, warn_abs, crit_abs, 0, total)]


check_info["rabbitmq_nodes.gc"] = LegacyCheckDefinition(
    name="rabbitmq_nodes_gc",
    service_name="RabbitMQ Node %s GC",
    sections=["rabbitmq_nodes"],
    discovery_function=discover_key("gc"),
    check_function=check_rabbitmq_nodes_gc,
    check_ruleset_name="rabbitmq_nodes_gc",
)
