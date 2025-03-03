#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal, TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    State,
)
from cmk.plugins.lib.rabbitmq import discover_key, Section

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


class Params(TypedDict):
    levels: (
        tuple[Literal["fd_abs"], tuple[int, int]]
        | tuple[Literal["fd_perc"], tuple[float, float]]
        | None
    )


RMQ_IO_METRICS_DROPPED_VERSION = "4.0.1"


def discover_rabbitmq_nodes_sockets(
    section_rabbitmq_nodes: Section | None, section_rabbitmq_cluster: Mapping[str, _ItemData] | None
) -> DiscoveryResult:
    if section_rabbitmq_nodes is None:
        return

    if (
        section_rabbitmq_cluster is None
        or (cluster_version := section_rabbitmq_cluster.get("info", {}).get("rabbitmq_version"))
        is None
        or int(cluster_version.split(".")[0])
        < int(RMQ_IO_METRICS_DROPPED_VERSION.split(".", maxsplit=1)[0])
    ):
        yield from discover_key("sockets")(section_rabbitmq_nodes)


def _apply_check_levels(
    check_value: float, levels_upper: tuple[int | float, int | float], summary: str
) -> CheckResult:
    for check_result in check_levels(value=check_value, levels_upper=("fixed", levels_upper)):
        if isinstance(check_result, Result):
            yield Result(state=check_result.state, summary=summary)


def _handle_output(
    used: float,
    total: float,
    level_config: None
    | tuple[Literal["fd_abs"], tuple[int, int]]
    | tuple[Literal["fd_perc"], tuple[float, float]],
    metric_name: str,
    summary_prefix: str,
) -> CheckResult:
    perc_value = 100.0 * used / total

    match level_config:
        case None:
            yield from check_levels(
                value=used,
                levels_upper=None,
                metric_name=metric_name,
                label=summary_prefix,
                render_func=lambda x: f"{x} of {total}, {render.percent(perc_value)}",
                boundaries=(0, total),
            )
        case ("fd_abs", (int(warn), int(crit))):
            summary = f"{summary_prefix}: {used} of {total}, {render.percent(perc_value)} (warn/crit at {warn}/{crit})"
            yield from _apply_check_levels(used, (warn, crit), summary)
            yield Metric(metric_name, used, levels=(warn, crit), boundaries=(0, total))
        case ("fd_perc", (float(warn), float(crit))):
            summary = f"{summary_prefix}: {used} of {total}, {render.percent(perc_value)} (warn/crit at {render.percent(warn)}/{render.percent(crit)})"
            yield from _apply_check_levels(perc_value, (warn, crit), summary)
            # construct perfdata for absolute values even when perc levels are set
            yield Metric(
                metric_name,
                used,
                levels=(int((warn / 100.0) * total), int((crit / 100.0) * total)),
                boundaries=(0, total),
            )
        case other:
            raise NotImplementedError(other)


def check_rabbitmq_nodes_sockets(
    item: str,
    params: Params,
    section_rabbitmq_nodes: Section | None,
    section_rabbitmq_cluster: Mapping[str, _ItemData] | None,
) -> CheckResult:
    if (
        section_rabbitmq_nodes is None
        or (socket_data := section_rabbitmq_nodes.get(item, {}).get("sockets")) is None
    ):
        return

    used = socket_data.get("sockets_used")
    if used is None:
        return

    total = socket_data.get("sockets_total")
    if total is None:
        return

    if total == 0:
        yield Result(state=State.CRIT, summary="No available sockets")
        return

    yield from _handle_output(used, total, params.get("levels"), "sockets", "Sockets used")


check_plugin_rabbitmq_nodes_proc = CheckPlugin(
    name="rabbitmq_nodes_sockets",
    service_name="RabbitMQ Node %s Sockets",
    sections=["rabbitmq_nodes", "rabbitmq_cluster"],
    discovery_function=discover_rabbitmq_nodes_sockets,
    check_function=check_rabbitmq_nodes_sockets,
    check_ruleset_name="rabbitmq_nodes_sockets",
    check_default_parameters={},
)
