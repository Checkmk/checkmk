#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from cmk.agent_based.v2 import render
from cmk.plugins.lib.memory import compute_state
from cmk.plugins.lib.memory import normalize_levels as normalize_mem_levels

memused_default_levels = (150.0, 200.0)

MEMORY_DEFAULT_LEVELS = {
    "levels": memused_default_levels,
}


def _compute_state(value: float, warn: float | None, crit: float | None) -> int:
    return int(compute_state(value, warn, crit))


#############################################################################
#    This function is already migrated and available in utils/memory.py !   #
#############################################################################
def check_memory_element(
    label: str,
    used: float,
    total: float,
    levels: tuple[Literal["abs_used", "abs_free", "perc_used", "perc_free"], tuple[float, float]]
    | None,
    label_total: str = "",
    show_free: bool = False,
    metric_name: str | None = None,
    create_percent_metric: bool = False,
) -> tuple[
    int, str, list[tuple[str, float, float | None, float | None, float | None, float | None]]
]:
    """Return a check result for one memory element"""
    if show_free:
        show_value = total - used
        show_text = " free"
    else:
        show_value = used
        show_text = ""

    infotext = "{}: {}{} - {} of {}{}".format(
        label,
        render.percent(100.0 * show_value / total),
        show_text,
        render.bytes(show_value),
        render.bytes(total),
        (" %s" % label_total).rstrip(),
    )

    try:
        mode, (warn, crit) = levels  # type: ignore[misc]
    except (ValueError, TypeError):  # handle None, "ignore"
        mode, (warn, crit) = "ignore", (None, None)

    warn, crit, levels_text = normalize_mem_levels(mode, warn, crit, total)
    state = _compute_state(used, warn, crit)
    if state and levels_text:
        infotext = f"{infotext} ({levels_text})"

    perf: list[tuple[str, float, float | None, float | None, float | None, float | None]] = []
    if metric_name:
        perf.append((metric_name, used, warn, crit, 0, total))
    if create_percent_metric:
        scale_to_perc = 100.0 / total
        perf.append(
            (
                "mem_used_percent",
                used * scale_to_perc,
                warn * scale_to_perc if warn is not None else None,
                crit * scale_to_perc if crit is not None else None,
                0,
                None,  # some times over 100%!
            )
        )

    return state, infotext, perf
