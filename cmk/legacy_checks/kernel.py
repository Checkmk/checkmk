#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    get_rate,
    get_value_store,
    NoLevelsT,
    Result,
    Service,
    State,
)
from cmk.plugins.collection.agent_based.kernel import KERNEL_COUNTER_NAMES, Section

_KERNEL_METRICS_NAMES = {
    "ctxt": "context_switches",
    "processes": "process_creations",
    "pgmajfault": "major_page_faults",
    "pswpin": "page_swap_in",
    "pswpout": "page_swap_out",
}


def _fixed_or_no_levels(
    levels: tuple[float | None, float | None] | None,
) -> NoLevelsT | FixedLevelsT[float]:
    if levels is None or levels[0] is None or levels[1] is None:
        return ("no_levels", None)
    return ("fixed", (levels[0], levels[1]))


def discover_kernel_performance(section: Section) -> DiscoveryResult:
    _, items = section
    for name in KERNEL_COUNTER_NAMES.values():
        if items.get(name):
            yield Service()
            return


def check_kernel_performance(params: Mapping[str, Any], section: Section) -> CheckResult:
    timestamp, items = section
    if timestamp is None:
        return

    for item_name in KERNEL_COUNTER_NAMES.values():
        item_values = items.get(item_name)
        if item_values is None:
            continue

        if len(item_values) > 1:
            yield Result(
                state=State.UNKNOWN,
                summary=f"item {item_name!r} not unique (found {len(item_values)} times)",
            )

        counter, value = item_values[0]
        if not isinstance(value, int):
            continue
        rate = get_rate(get_value_store(), counter, timestamp, value, raise_overflow=True)
        metric_name = _KERNEL_METRICS_NAMES[counter]

        if counter in ("pswpin", "pswpout"):
            yield from check_levels(
                rate,
                metric_name=metric_name,
                levels_upper=_fixed_or_no_levels(params.get(f"{metric_name}_levels")),
                levels_lower=_fixed_or_no_levels(params.get(f"{metric_name}_levels_lower")),
                render_func=lambda x: f"{x:.2f}/s",
                label=item_name,
                boundaries=(0, None),
            )
        else:
            yield from check_levels(
                rate,
                metric_name=metric_name,
                levels_upper=_fixed_or_no_levels(params.get(counter)),
                render_func=lambda x: f"{x:.2f}/s",
                label=item_name,
                boundaries=(0, None),
            )


check_plugin_kernel_performance = CheckPlugin(
    name="kernel_performance",
    service_name="Kernel Performance",
    sections=["kernel"],
    discovery_function=discover_kernel_performance,
    check_function=check_kernel_performance,
    check_ruleset_name="kernel_performance",
    check_default_parameters={},
)
