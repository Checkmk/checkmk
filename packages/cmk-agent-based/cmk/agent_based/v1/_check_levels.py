#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Generator, Mapping
from typing import Literal, overload

from cmk.agent_based.prediction_backend import (
    InjectedParameters,
    lookup_predictive_levels,
    PredictionParameters,
)

from ._checking_classes import Metric, Result, State

# ruff: noqa: PLR0913


def _do_check_levels(
    value: float,
    levels_upper: tuple[float, float] | None,
    levels_lower: tuple[float, float] | None,
    render_func: Callable[[float], str],
) -> tuple[State, str]:
    # Typing says that levels are either None, or a Tuple of float.
    # However we also deal with (None, None) to avoid crashes of custom plug-ins.
    # CRIT ?
    if levels_upper and levels_upper[1] is not None and value >= levels_upper[1]:
        return State.CRIT, _levelsinfo_ty("at", levels_upper, render_func)
    if levels_lower and levels_lower[1] is not None and value < levels_lower[1]:
        return State.CRIT, _levelsinfo_ty("below", levels_lower, render_func)

    # WARN ?
    if levels_upper and levels_upper[0] is not None and value >= levels_upper[0]:
        return State.WARN, _levelsinfo_ty("at", levels_upper, render_func)
    if levels_lower and levels_lower[0] is not None and value < levels_lower[0]:
        return State.WARN, _levelsinfo_ty("below", levels_lower, render_func)

    return State.OK, ""


def _levelsinfo_ty(
    preposition: str, levels: tuple[float, float], render_func: Callable[[float], str]
) -> str:
    # Again we are forgiving if we get passed 'None' in the levels.
    warn_str = "never" if levels[0] is None else render_func(levels[0])
    crit_str = "never" if levels[1] is None else render_func(levels[1])
    return f" (warn/crit {preposition} {warn_str}/{crit_str})"


def _default_rendering(x: float) -> str:
    return f"{x:.2f}"


@overload
def check_levels(
    value: float,
    *,
    levels_upper: tuple[float, float] | None = None,
    levels_lower: tuple[float, float] | None = None,
    metric_name: None = None,
    render_func: Callable[[float], str] | None = None,
    label: str | None = None,
    boundaries: tuple[float | None, float | None] | None = None,
    notice_only: bool = False,
) -> Generator[Result, None, None]:
    pass


@overload
def check_levels(
    value: float,
    *,
    levels_upper: tuple[float, float] | None = None,
    levels_lower: tuple[float, float] | None = None,
    metric_name: str = "",
    render_func: Callable[[float], str] | None = None,
    label: str | None = None,
    boundaries: tuple[float | None, float | None] | None = None,
    notice_only: bool = False,
) -> Generator[Result | Metric, None, None]:
    pass


def check_levels(
    value: float,
    *,
    levels_upper: tuple[float, float] | None = None,
    levels_lower: tuple[float, float] | None = None,
    metric_name: str | None = None,
    render_func: Callable[[float], str] | None = None,
    label: str | None = None,
    boundaries: tuple[float | None, float | None] | None = None,
    notice_only: bool = False,
) -> Generator[Result | Metric, None, None]:
    """Generic function for checking a value against levels.

    Args:

        value:        The currently measured value
        levels_upper: A pair of upper thresholds, ie. warn and crit. If value is larger than these,
                      the service goes to **WARN** or **CRIT**, respecively.
        levels_lower: A pair of lower thresholds, ie. warn and crit. If value is smaller than these,
                      the service goes to **WARN** or **CRIT**, respecively.
        metric_name:  The name of the datasource in the RRD that corresponds to this value
                      or None in order not to generate a metric.
        render_func:  A single argument function to convert the value from float into a
                      human readable string.
        label:        The label to prepend to the output.
        boundaries:   Minimum and maximum to add to the metric.
        notice_only:  Only show up in service output if not OK (otherwise in details).
                      See `notice` keyword of `Result` class.

    Example:

        >>> result, metric = check_levels(
        ...     23.0,
        ...     levels_upper=(12., 42.),
        ...     metric_name="temperature",
        ...     label="Fridge",
        ...     render_func=lambda v: "%.1f°" % v,
        ... )
        >>> print(result.summary)
        Fridge: 23.0° (warn/crit at 12.0°/42.0°)
        >>> print(metric)
        Metric('temperature', 23.0, levels=(12.0, 42.0))

    """

    if render_func is None:
        render_func = _default_rendering

    info_text = str(render_func(value))  # forgive wrong output type
    if label:
        info_text = f"{label}: {info_text}"

    value_state, levels_text = _do_check_levels(value, levels_upper, levels_lower, render_func)

    if notice_only:
        yield Result(state=value_state, notice=info_text + levels_text)
    else:
        yield Result(state=value_state, summary=info_text + levels_text)
    if metric_name:
        yield Metric(metric_name, value, levels=levels_upper, boundaries=boundaries)


def check_levels_predictive(
    value: float,
    *,
    levels: dict[str, object],
    metric_name: str,
    render_func: Callable[[float], str] | None = None,
    label: str | None = None,
    boundaries: tuple[float | None, float | None] | None = None,
) -> Generator[Result | Metric, None, None]:
    """Generic function for checking a value against levels.

    Args:

        value:        Currently measured value
        levels:       Predictive levels. These are used automatically.
                      Lower levels are imposed if the passed dictionary contains "levels_lower"
                      as key, upper levels are imposed if it contains "levels_upper".
                      If value is lower/higher than these, the service goes to **WARN**
                      or **CRIT**, respecively.
        metric_name:  Name of the datasource in the RRD that corresponds to this value
        render_func:  Single argument function to convert the value from float into a
                      human readable string.
                      readable fashion
        label:        Label to prepend to the output.
        boundaries:   Minimum and maximum to add to the metric.

    """
    if render_func is None:
        render_func = _default_rendering

    # validate the metric name, before we can get the levels.
    _ = Metric(metric_name, value)

    ref_value_upper, levels_upper = _get_prediction(metric_name, levels, "upper")
    ref_value_lower, levels_lower = _get_prediction(metric_name, levels, "lower")

    ref_value = ref_value_upper or ref_value_lower  # they are the same in the v1 world
    if ref_value is not None:
        predictive_levels_msg = f" (predicted reference: {render_func(ref_value)})"
    else:
        predictive_levels_msg = " (no reference for prediction yet)"

    value_state, levels_text = _do_check_levels(value, levels_upper, levels_lower, render_func)

    if label:
        info_text = f"{label}: {render_func(value)}{predictive_levels_msg}"
    else:
        info_text = f"{render_func(value)}{predictive_levels_msg}"

    yield Result(state=value_state, summary=info_text + levels_text)
    yield Metric(metric_name, value, levels=levels_upper, boundaries=boundaries)
    if ref_value is not None:
        yield Metric(f"predict_{metric_name}", ref_value)


def _get_prediction(
    metric_name: str, levels: Mapping[str, object], direction: Literal["upper", "lower"]
) -> tuple[float | None, tuple[float, float] | None]:
    return (
        (None, None)
        if (levels_spec := levels.get(f"levels_{direction}")) is None
        else lookup_predictive_levels(
            metric_name,
            direction,
            PredictionParameters.model_validate(
                {  # type: ignore[misc]
                    "horizon": levels["horizon"],
                    "period": levels["period"],
                    "levels": levels_spec,
                    "bound": levels.get("levels_upper_min") if direction == "upper" else None,
                }
            ),
            InjectedParameters.model_validate(levels["__injected__"]),
        )
    )
