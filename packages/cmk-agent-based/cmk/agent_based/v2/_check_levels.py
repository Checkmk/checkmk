#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from enum import Enum, StrEnum
from typing import assert_never, Literal, NotRequired, overload, TypedDict

from cmk.agent_based.prediction_backend import (
    InjectedParameters,
    lookup_predictive_levels,
    PredictionParameters,
)

from ..v1 import Metric, Result, State

_NoLevels = tuple[Literal["no_levels"], None]

_FixedLevels = tuple[Literal["fixed"], tuple[int, int] | tuple[float, float]]


class _PredictiveModel(TypedDict):
    period: Literal["wday", "day", "hour", "minute"]
    horizon: int
    levels: tuple[Literal["absolute", "relative", "stdev"], tuple[float, float]]
    bound: NotRequired[tuple[float, float] | None]
    __injected__: Mapping[str, object] | None


_PredictiveLevels = tuple[Literal["predictive"], _PredictiveModel]


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
    levels: tuple[int | int] | tuple[float, float] | None = None
    levels_text: str = ""
    prediction: float | None = None


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
    levels_params: _PredictiveModel,
    levels_direction: Direction,
    metric_name: str,
    render_func: Callable[[float], str],
) -> CheckLevelsResult:
    (  # pylint: disable=assignment-from-no-return,unpacking-non-sequence
        prediction,
        levels,
    ) = lookup_predictive_levels(
        metric_name,
        levels_direction.value,
        PredictionParameters.model_validate(levels_params),
        InjectedParameters.model_validate(levels_params["__injected__"]),
    )

    if levels is None:
        return CheckLevelsResult(
            type=Type.PREDICTIVE, state=State.OK, levels=None, levels_text="", prediction=prediction
        )

    return replace(
        _check_fixed_levels(value, levels, levels_direction, render_func),
        type=Type.PREDICTIVE,
        prediction=prediction,
    )


def _check_levels(
    value: float,
    levels: _NoLevels | _FixedLevels | _PredictiveLevels | None,
    levels_direction: Direction,
    render_func: Callable[[float], str],
    metric_name: str | None,
) -> CheckLevelsResult:
    if levels is None:
        return CheckLevelsResult(Type.NO_LEVELS, State.OK)

    levels_type, levels_model = levels

    match levels_type:
        case "no_levels":
            return CheckLevelsResult(Type.NO_LEVELS, State.OK)
        case "fixed":
            if not isinstance(levels_model, tuple):
                raise TypeError("Incorrect level parameters")

            return _check_fixed_levels(value, levels_model, levels_direction, render_func)
        case "predictive":
            if not isinstance(metric_name, str):
                raise TypeError("Metric name can't be `None` if predictive levels are used.")

            if not isinstance(levels_model, dict):
                raise TypeError("Incorrect level parameters")

            return _check_predictive_levels(
                value, levels_model, levels_direction, metric_name, render_func
            )
        case other:
            assert_never(other)


def _prediction_text(prediction: float | None, render_func: Callable[[float], str]) -> str:
    rendered = render_func(prediction) if prediction is not None else "N/A"
    return f"prediction: {rendered}"


def _summarize_predictions(
    upper_result: CheckLevelsResult,
    lower_result: CheckLevelsResult,
    metric_name: str | None,
    render_func: Callable[[float], str],
) -> tuple[Mapping[str, float], str]:
    if (Type.PREDICTIVE not in (upper_result.type, lower_result.type)) or metric_name is None:
        return {}, ""

    predictions = [p for p in (upper_result.prediction, lower_result.prediction) if p is not None]

    if len(predictions) == 0:
        return {}, f"({_prediction_text(None, render_func)})"

    if len(predictions) == 1 or predictions[0] == predictions[1]:
        metrics = {f"predict_{metric_name}": predictions[0]}
        return metrics, f"({_prediction_text(predictions[0], render_func)})"

    metrics = {
        f"predict_{metric_name}": predictions[0],
        f"predict_lower_{metric_name}": predictions[1],
    }
    upper_text = _prediction_text(predictions[0], render_func)
    lower_text = _prediction_text(predictions[1], render_func)
    return metrics, f"(upper levels {upper_text}, lower levels {lower_text})"


@overload
def check_levels(  # pylint: disable=too-many-arguments
    value: float,
    *,
    levels_upper: _NoLevels | _FixedLevels | None = None,
    levels_lower: _NoLevels | _FixedLevels | None = None,
    metric_name: None = None,
    render_function: Callable[[float], str] | None = None,
    label: str | None = None,
    boundaries: tuple[float | None, float | None] | None = None,
    notice_only: bool = False,
) -> Iterable[Result]:
    pass


@overload
def check_levels(  # pylint: disable=too-many-arguments
    value: float,
    *,
    levels_upper: _NoLevels | _FixedLevels | _PredictiveLevels | None = None,
    levels_lower: _NoLevels | _FixedLevels | _PredictiveLevels | None = None,
    metric_name: str = "",
    render_function: Callable[[float], str] | None = None,
    label: str | None = None,
    boundaries: tuple[float | None, float | None] | None = None,
    notice_only: bool = False,
) -> Iterable[Result | Metric]:
    pass


def check_levels(  # pylint: disable=too-many-arguments,too-many-locals
    value: float,
    *,
    levels_upper: _NoLevels | _FixedLevels | _PredictiveLevels | None = None,
    levels_lower: _NoLevels | _FixedLevels | _PredictiveLevels | None = None,
    metric_name: str | None = None,
    render_function: Callable[[float], str] | None = None,
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
        render_function:  A single argument function to convert the value from float into a
                      human readable string.
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
        ...     render_function=lambda v: "%.1f°" % v,
        ... )
        >>> print(result.summary)
        Fridge: 23.0° (warn/crit at 12.0°/42.0°)
        >>> print(metric)
        Metric('temperature', 23.0, levels=(12.0, 42.0))

    """
    render_func = render_function if render_function else _default_rendering
    value_string = render_func(value)
    info_text = f"{label}: {value_string}" if label else value_string

    result_upper = _check_levels(value, levels_upper, Direction.UPPER, render_func, metric_name)
    result_lower = _check_levels(value, levels_lower, Direction.LOWER, render_func, metric_name)

    state = State.worst(result_upper.state, result_lower.state)
    prediction_metrics, prediction_text = _summarize_predictions(
        result_upper, result_lower, metric_name, render_func
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
            levels=result_upper.levels,  # type: ignore[arg-type]
            boundaries=boundaries,
        )

    for prediction_metric, prediction_value in prediction_metrics.items():
        yield Metric(prediction_metric, prediction_value)
