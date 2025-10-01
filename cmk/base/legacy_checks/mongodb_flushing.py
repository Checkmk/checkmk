#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# <<<mongodb_flushing>>>
# average_ms 1.28893335892
# last_ms 0
# flushed 36479


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_average,
    get_value_store,
    render,
    Result,
    Service,
    State,
    StringTable,
)


def inventory_mongodb_flushing(section: StringTable) -> DiscoveryResult:
    # This check has no default parameters
    # The average/last flush time highly depends on the size of the mongodb setup
    yield Service()


def check_mongodb_flushing(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    info_dict = dict(section)

    if not {"last_ms", "average_ms", "flushed"} <= set(info_dict):  # check if keys in dict
        yield Result(
            state=State.UNKNOWN,
            summary="missing data: %s"
            % (_get_missing_keys(["last_ms", "average_ms", "flushed"], info_dict)),
        )
        return

    try:
        last_ms = float(info_dict["last_ms"])
        avg_flush_time = float(info_dict["average_ms"]) / 1000.0
        flushed = int(info_dict["flushed"])
    except (ValueError, TypeError):
        yield Result(
            state=State.UNKNOWN,
            summary="Invalid data: last_ms: {}, average_ms: {}, flushed:{}".format(
                info_dict["last_ms"],
                info_dict["average_ms"],
                info_dict["flushed"],
            ),
        )
        return

    if "average_time" in params:
        warn, crit, avg_interval = params["average_time"]
        avg_ms_compute = get_average(
            get_value_store(), "flushes", time.time(), last_ms, avg_interval
        )
        yield from check_levels(
            avg_ms_compute,
            levels_upper=("fixed", (warn, crit)),
            render_func=lambda x: f"{x:.1f} ms",
            label=f"Average flush time over {avg_interval} minutes",
        )

    yield from check_levels(
        (last_ms / 1000.0),
        metric_name="flush_time",
        levels_upper=(
            ("fixed", levels) if (levels := params.get("last_time")) else ("no_levels", None)
        ),
        render_func=lambda x: f"{x:.2f} s",
        label="Last flush time",
    )

    yield from check_levels(flushed, metric_name="flushed", label="Flushes since restart")
    yield from check_levels(
        avg_flush_time,
        metric_name="avg_flush_time",
        label="Average flush time",
        render_func=render.timespan,
    )


def _get_missing_keys(key_list, info_dict):
    missing_keys = []
    for key in key_list:
        if key not in info_dict:
            missing_keys += [str(key)]
    return " and ".join(sorted(missing_keys))


def parse_mongodb_flushing(string_table: StringTable) -> StringTable:
    return string_table


agent_section_mongodb_flushing = AgentSection(
    name="mongodb_flushing",
    parse_function=parse_mongodb_flushing,
)


check_plugin_mongodb_flushing = CheckPlugin(
    name="mongodb_flushing",
    service_name="MongoDB Flushing",
    discovery_function=inventory_mongodb_flushing,
    check_function=check_mongodb_flushing,
    check_ruleset_name="mongodb_flushing",
    check_default_parameters={},
)
