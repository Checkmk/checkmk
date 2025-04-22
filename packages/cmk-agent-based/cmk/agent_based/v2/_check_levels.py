#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from enum import Enum, StrEnum
from typing import Literal

from cmk.agent_based.v1 import Metric, Result, State

NoLevelsT = tuple[Literal["no_levels"], None]

type FixedLevelsT[_NumberT: (int, float)] = tuple[Literal["fixed"], tuple[_NumberT, _NumberT]]

type PredictiveLevelsT[_NumberT: (int, float)] = tuple[
    Literal["predictive"], tuple[str, float | None, tuple[_NumberT, _NumberT] | None]
]

type LevelsT[_NumberT: (int, float)] = (
    NoLevelsT | FixedLevelsT[_NumberT] | PredictiveLevelsT[_NumberT]
)


class Direction(StrEnum):
    UPPER = "upper"
    LOWER = "lower"


class Type(Enum):
    NO_LEVELS = 0
    FIXED = 1
    PREDICTIVE = 2


@dataclass(frozen=True)
class CheckLevelsResult:
    type: Type
    state: State
    levels: tuple[int, int] | tuple[float, float] | None = None
    levels_text: str = ""
    prediction: Metric | None = None


def _default_rendering(x: float) -> str:
    return f"{x:.2f}"


def _levels_text(
    levels: tuple[int, int] | tuple[float, float],
    levels_direction: Direction,
    render_func: Callable[[float], str],
) -> str:
    preposition = "at" if levels_direction == Direction.UPPER else "below"
    warn_str, crit_str = render_func(levels[0]), render_func(levels[1])
    return f"(warn/crit {preposition} {warn_str}/{crit_str})"


def _check_fixed_levels(
    value: float,
    levels: tuple[int, int] | tuple[float, float],
    levels_direction: Direction,
    render_func: Callable[[float], str],
) -> CheckLevelsResult:
    warn_level, crit_level = levels
    levels_text = _levels_text(levels, levels_direction, render_func)

    if levels_direction == Direction.UPPER:
        if value >= crit_level:
            return CheckLevelsResult(Type.FIXED, State.CRIT, levels, levels_text)
        if value >= warn_level:
            return CheckLevelsResult(Type.FIXED, State.WARN, levels, levels_text)
    else:
        if value < crit_level:
            return CheckLevelsResult(Type.FIXED, State.CRIT, levels, levels_text)
        if value < warn_level:
            return CheckLevelsResult(Type.FIXED, State.WARN, levels, levels_text)

    return CheckLevelsResult(Type.FIXED, State.OK, levels)


def _check_predictive_levels(
    value: float,
    metric_name: str,
    predicted_value: float | None,
    levels: tuple[float, float] | None,
    levels_direction: Direction,
    render_func: Callable[[float], str],
) -> CheckLevelsResult:
    if levels is None:
        return CheckLevelsResult(
            type=Type.PREDICTIVE,
            state=State.OK,
            levels=None,
            levels_text="",
            prediction=_make_prediction_metric(metric_name, predicted_value, levels_direction),
        )

    return replace(
        _check_fixed_levels(value, levels, levels_direction, render_func),
        type=Type.PREDICTIVE,
        prediction=_make_prediction_metric(metric_name, predicted_value, levels_direction),
    )


def _make_prediction_metric(name: str, value: float | None, direction: Direction) -> Metric | None:
    if value is None:
        return None
    if direction is Direction.UPPER:
        return Metric(f"predict_{name}", value)
    return Metric(f"predict_lower_{name}", value)


def _check_levels[_NumberT: (int, float)](
    value: float,
    levels: LevelsT[_NumberT] | None,
    levels_direction: Direction,
    render_func: Callable[[float], str],
) -> CheckLevelsResult:
    # mypy does not properly narrow tuples types, so we need a couple of asserts.
    # They are only for mypy though.
    match levels:
        case None | ("no_levels", None):
            return CheckLevelsResult(Type.NO_LEVELS, State.OK)

        case "fixed", (warn, crit):
            assert isinstance(warn, float | int) and isinstance(crit, float | int)
            return _check_fixed_levels(value, (warn, crit), levels_direction, render_func)

        case "predictive", (metric, prediction, p_levels):
            assert isinstance(metric, str)
            # we expect `float`, but since typing does not prevent us from passing `int`, be nice
            assert prediction is None or isinstance(prediction, float | int)
            assert p_levels is None or isinstance(p_levels, tuple)
            return _check_predictive_levels(
                value, metric, prediction, p_levels, levels_direction, render_func
            )

        case other:
            raise TypeError(f"Incorrect level parameters: {other!r}")


def _prediction_text(prediction: float | None, render_func: Callable[[float], str]) -> str:
    rendered = render_func(prediction) if prediction is not None else "N/A"
    return f"prediction: {rendered}"


def _summarize_predictions(
    upper_result: CheckLevelsResult,
    lower_result: CheckLevelsResult,
    render_func: Callable[[float], str],
) -> tuple[Sequence[Metric], str]:
    if Type.PREDICTIVE not in (upper_result.type, lower_result.type):
        return (), ""

    predictions = [p for p in (upper_result.prediction, lower_result.prediction) if p is not None]

    if not predictions:
        return (), f"({_prediction_text(None, render_func)})"

    if len(predictions) == 1 or predictions[0].value == predictions[1].value:
        return predictions, f"({_prediction_text(predictions[0].value, render_func)})"

    upper_text = _prediction_text(predictions[0].value, render_func)
    lower_text = _prediction_text(predictions[1].value, render_func)
    return predictions, f"(upper levels {upper_text}, lower levels {lower_text})"


def check_levels[_NumberT: (int, float)](
    value: float,
    *,
    levels_upper: LevelsT[_NumberT] | None = None,
    levels_lower: LevelsT[_NumberT] | None = None,
    metric_name: str | None = None,
    render_func: Callable[[float], str] | None = None,
    label: str | None = None,
    boundaries: tuple[float | None, float | None] | None = None,
    notice_only: bool = False,
) -> Iterable[Result | Metric]:
    """Generic function for checking a value against levels.

    Args:

        value:        The currently measured value
        levels_upper: Upper level parameters created by the :class:Levels form spec
        levels_lower: Lower level parameters created by the :class:Levels form spec
        metric_name:  The name of the datasource in the RRD that corresponds to this value
                      or None in order not to generate a metric.
        render_func:  A single argument function to convert the value from float into a
                      human-readable string.
        label:        The label to prepend to the output.
        boundaries:   Minimum and maximum to add to the metric.
        notice_only:  Only show up in service output if not OK (otherwise in details).
                      See `notice` keyword of `Result` class.

    Example:

        >>> result, metric = check_levels(
        ...     23.0,
        ...     levels_upper=("fixed", (12., 42.)),
        ...     metric_name="temperature",
        ...     label="Fridge",
        ...     render_func=lambda v: "%.1f°" % v,
        ... )
        >>> print(result.summary)
        Fridge: 23.0° (warn/crit at 12.0°/42.0°)
        >>> print(metric)
        Metric('temperature', 23.0, levels=(12.0, 42.0))

    """
    render_func = render_func if render_func else _default_rendering
    value_string = render_func(value)
    info_text = f"{label}: {value_string}" if label else value_string

    result_upper = _check_levels(value, levels_upper, Direction.UPPER, render_func)
    result_lower = _check_levels(value, levels_lower, Direction.LOWER, render_func)

    state = State.worst(result_upper.state, result_lower.state)
    prediction_metrics, prediction_text = _summarize_predictions(
        result_upper, result_lower, render_func
    )

    messages = [info_text, prediction_text, result_upper.levels_text, result_lower.levels_text]
    summary = " ".join(m for m in messages if m)

    if notice_only:
        yield Result(state=state, notice=summary)
    else:
        yield Result(state=state, summary=summary)

    if metric_name:
        yield Metric(
            metric_name,
            value,
            levels=result_upper.levels,
            boundaries=boundaries,
        )
    yield from prediction_metrics
