#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypedDict

from cmk.agent_based.v2 import CheckResult, Metric, render, Result, State

_LevelsMode = Literal["abs_used", "abs_free", "perc_used", "perc_free"]
MemoryLevels = tuple[_LevelsMode, tuple[float | None, float | None]]

SectionMem = Mapping[str, int]


class SectionMemUsed(TypedDict, total=False):
    Cached: int
    MemFree: int
    MemTotal: int
    SwapFree: int
    SwapTotal: int


@dataclass
class SectionMemTotal:
    memory_total: int

    def get(self, key: Literal["MemTotal"]) -> int:
        # this is a compatibility layer with the mem and mem_used sections
        # which makes it a bit easiert to work with this in the ps check
        # you should never call this method in another context!
        return self.memory_total


def is_linux_section(section: SectionMem) -> bool:
    # match these to the keys required by checks/mem
    return {
        "Buffers",
        "Cached",
        "Dirty",
        "MemFree",
        "MemTotal",
        "SwapFree",
        "SwapTotal",
        "Writeback",
    } <= section.keys()


def get_levels_mode_from_value(warn: float | None) -> _LevelsMode:
    """get levels mode by looking at the value

    Levels may be given either as
     * positive int -> absolute levels on used
     * negative int -> absolute levels on free
     * positive float -> percentages on used
     * negative float -> percentages on free

        >>> get_levels_mode_from_value(-23.)
        'perc_free'
        >>> get_levels_mode_from_value(23)
        'abs_used'

    """
    used_level = warn is not None and warn > 0
    if isinstance(warn, float):  # percent
        return "perc_used" if used_level else "perc_free"
    return "abs_used" if used_level else "abs_free"


def normalize_levels(
    mode: _LevelsMode,
    warn: float | None,
    crit: float | None,
    total: float,
    _perc_total: float | None = None,
    render_unit: int = 1,
) -> tuple[float, float, str] | tuple[None, None, str]:
    """get normalized levels and formatter

    Levels may be given either as
     * Absolute levels on used
     * Absolute levels on free
     * Percentage levels on used
     * Percentage levels on free
    Normalize levels to absolute posive levels and return formatted levels text

        >>> normalize_levels("perc_used", 12, 42, 200)
        (24.0, 84.0, 'warn/crit at 12.00%/42.00% used')

    """
    # TODO: remove this weird case of different reference values.
    if _perc_total is None:
        _perc_total = total

    if warn is None or crit is None:
        return None, None, ""

    mode_split = mode.split("_", 1)
    if mode_split[0] not in ("perc", "abs") or mode_split[-1] not in ("used", "free"):
        raise NotImplementedError(f"unknown levels mode: {mode!r}")

    # normalize percent -> absolute
    if mode.startswith("perc"):
        warn_used = warn / 100.0 * _perc_total
        crit_used = crit / 100.0 * _perc_total
        levels_text = f"{render.percent(warn)}/{render.percent(crit)}"
    else:  # absolute
        warn_used = float(warn)
        crit_used = float(crit)
        levels_text = f"{render.bytes(warn * render_unit)}/{render.bytes(crit * render_unit)}"

    # normalize free -> used
    if mode.endswith("free"):
        warn_used = float(total - warn_used)
        crit_used = float(total - crit_used)
        levels_text = "warn/crit below %s free" % levels_text
    else:  # used
        levels_text = "warn/crit at %s used" % levels_text

    return warn_used, crit_used, levels_text


def compute_state(value: float, warn: float | None, crit: float | None) -> State:
    """get state according to levels

    >>> print(compute_state(23., 12, 42))
    State.WARN

    """
    if crit is not None and value >= crit:
        return State.CRIT
    if warn is not None and value >= warn:
        return State.WARN
    return State.OK


def check_element(
    label: str,
    used: float,
    total: float,
    # levels: we can deal with anything, though
    levels: MemoryLevels | None = None,
    label_total: str = "",
    show_free: bool = False,
    metric_name: str | None = None,
    create_percent_metric: bool = False,
) -> CheckResult:
    """Yield a check result and metric for one memory element

    >>> result, metric = check_element(
    ...     label="Short term memory",
    ...     used=46,
    ...     total=200.,
    ...     levels=("perc_used", (12, 42)),
    ...     create_percent_metric=True,
    ... )
    >>> print(result.summary)
    Short term memory: 23.00% - 46 B of 200 B (warn/crit at 12.00%/42.00% used)
    >>> print(result.state)
    State.WARN
    >>> print(metric)
    Metric('mem_used_percent', 23.0, levels=(12.0, 42.0), boundaries=(0.0, None))

    """
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
        warn, crit, levels_text = None, None, ""
    else:
        warn, crit, levels_text = normalize_levels(mode, warn, crit, total)

    my_state = compute_state(used, warn, crit)
    if my_state != State.OK and levels_text:
        infotext = f"{infotext} ({levels_text})"
    yield Result(state=my_state, summary=infotext)

    if metric_name:
        yield Metric(metric_name, used, levels=(warn, crit), boundaries=(0, total))

    if create_percent_metric:
        scale_to_perc = 100.0 / total
        yield Metric(
            "mem_used_percent",
            used * scale_to_perc,
            levels=(
                warn * scale_to_perc if warn is not None else None,
                crit * scale_to_perc if crit is not None else None,
            ),
            boundaries=(0.0, None),  # some times over 100%!
        )
