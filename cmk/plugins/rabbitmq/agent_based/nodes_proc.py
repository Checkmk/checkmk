#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import check_levels, CheckPlugin, CheckResult, Metric, render, Result
from cmk.plugins.lib.rabbitmq import discover_key, Section


def check_rabbitmq_nodes_proc(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    proc_data = section.get(item, {}).get("proc")
    if not proc_data:
        return

    if (used := proc_data.get("proc_used")) is None:
        return

    if (total := proc_data.get("proc_total")) is None:
        return

    perc_value = 100.0 * used / total

    if (levels := params.get("levels")) is None or levels[1][0] == "no_levels":
        yield from check_levels(
            value=used,
            levels_upper=None,
            metric_name="processes",
            label="Erlang processes used",
            render_func=lambda x: f"{x} of {total}, {render.percent(perc_value)}",
            boundaries=(0, total),
        )
        return

    level_choice, (level_type, (warn, crit)) = levels

    if level_choice == "fd_abs":
        check_value = used
        metric_levels = (warn, crit)
        summary = f"Erlang processes used: {used} of {total}, {render.percent(perc_value)} (warn/crit at {warn}/{crit})"
    elif level_choice == "fd_perc":
        check_value = perc_value
        # construct perfdata for absolute values even when perc levels are set
        metric_levels = (int((warn / 100.0) * total), int((crit / 100.0) * total))
        summary = f"Erlang processes used: {used} of {total}, {render.percent(perc_value)} (warn/crit at {render.percent(warn)}/{render.percent(crit)})"
    else:
        raise NotImplementedError(level_choice)

    for check_result in check_levels(value=check_value, levels_upper=(level_type, (warn, crit))):
        if isinstance(check_result, Result):
            yield Result(state=check_result.state, summary=summary)
    yield Metric("processes", used, levels=metric_levels, boundaries=(0, total))


check_plugin_rabbitmq_nodes_proc = CheckPlugin(
    name="rabbitmq_nodes_proc",
    service_name="RabbitMQ Node %s Processes",
    sections=["rabbitmq_nodes"],
    discovery_function=discover_key("proc"),
    check_function=check_rabbitmq_nodes_proc,
    check_ruleset_name="rabbitmq_nodes_proc",
    check_default_parameters={},
)
