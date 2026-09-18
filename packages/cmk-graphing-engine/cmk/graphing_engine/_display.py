#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from typing import assert_never

from cmk.graphing.v1 import metrics as metrics_v1

from ._units import (
    AutoPrecision,
    CurveAttributes,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    Notation,
    Precision,
    SINotation,
    StandardScientificNotation,
    StrictPrecision,
    TimeNotation,
    Unit,
)

_COLORS: dict[metrics_v1.Color, str] = {
    metrics_v1.Color.LIGHT_RED: "#f37c7c",
    metrics_v1.Color.RED: "#ed3b3b",
    metrics_v1.Color.DARK_RED: "#a82a2a",
    metrics_v1.Color.LIGHT_ORANGE: "#ffad54",
    metrics_v1.Color.ORANGE: "#ff8400",
    metrics_v1.Color.DARK_ORANGE: "#b55e00",
    metrics_v1.Color.LIGHT_YELLOW: "#ffe456",
    metrics_v1.Color.YELLOW: "#ffd703",
    metrics_v1.Color.DARK_YELLOW: "#ac7c02",
    metrics_v1.Color.LIGHT_GREEN: "#62e0bf",
    metrics_v1.Color.GREEN: "#15d1a0",
    metrics_v1.Color.DARK_GREEN: "#0f9472",
    metrics_v1.Color.LIGHT_BLUE: "#6fc1f7",
    metrics_v1.Color.BLUE: "#28a2f3",
    metrics_v1.Color.DARK_BLUE: "#1c73ad",
    metrics_v1.Color.LIGHT_CYAN: "#68eeee",
    metrics_v1.Color.CYAN: "#1ee6e6",
    metrics_v1.Color.DARK_CYAN: "#17b5b5",
    metrics_v1.Color.LIGHT_PURPLE: "#acaaff",
    metrics_v1.Color.PURPLE: "#8380ff",
    metrics_v1.Color.DARK_PURPLE: "#5d5bb5",
    metrics_v1.Color.LIGHT_PINK: "#f9a8e2",
    metrics_v1.Color.PINK: "#ec48b6",
    metrics_v1.Color.DARK_PINK: "#be187a",
    metrics_v1.Color.LIGHT_BROWN: "#d4ad84",
    metrics_v1.Color.BROWN: "#bf8548",
    metrics_v1.Color.DARK_BROWN: "#885e33",
    metrics_v1.Color.LIGHT_GRAY: "#acacac",
    metrics_v1.Color.GRAY: "#8c8c8c",
    metrics_v1.Color.DARK_GRAY: "#5d5d5d",
    metrics_v1.Color.BLACK: "#1e262e",
    metrics_v1.Color.WHITE: "#ffffff",
}


def parse_color(color: metrics_v1.Color) -> str:
    return _COLORS[color]


def parse_unit(unit: metrics_v1.Unit) -> Unit:
    notation: Notation
    match unit.notation:
        case metrics_v1.DecimalNotation(symbol):
            notation = DecimalNotation(symbol)
        case metrics_v1.SINotation(symbol):
            notation = SINotation(symbol)
        case metrics_v1.IECNotation(symbol):
            notation = IECNotation(symbol)
        case metrics_v1.StandardScientificNotation(symbol):
            notation = StandardScientificNotation(symbol)
        case metrics_v1.EngineeringScientificNotation(symbol):
            notation = EngineeringScientificNotation(symbol)
        case metrics_v1.TimeNotation():
            notation = TimeNotation()
        case _:
            assert_never(unit.notation)

    precision: Precision
    match unit.precision:
        case metrics_v1.AutoPrecision(digits):
            precision = AutoPrecision(digits)
        case metrics_v1.StrictPrecision(digits):
            precision = StrictPrecision(digits)
        case _:
            assert_never(unit.precision)

    return Unit(notation=notation, precision=precision)


FALLBACK_COLOR = _COLORS[metrics_v1.Color.GRAY]
FALLBACK_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))
FALLBACK_ATTRIBUTES = CurveAttributes(title="", unit=FALLBACK_UNIT, color=FALLBACK_COLOR)


PREDICT_PREFIX = "predict_"
PREDICT_LOWER_PREFIX = "predict_lower_"


def _predicted_of(metric_name: str) -> tuple[str, str] | None:
    if metric_name.startswith(PREDICT_LOWER_PREFIX):
        return metric_name[len(PREDICT_LOWER_PREFIX) :], " (lower levels)"
    if metric_name.startswith(PREDICT_PREFIX):
        return metric_name[len(PREDICT_PREFIX) :], " (upper levels)"
    return None


def _declared_attributes(
    metric_name: str,
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
) -> CurveAttributes:
    if (definition := registered_metrics.get(metric_name)) is None:
        return CurveAttributes(title=metric_name, unit=FALLBACK_UNIT, color=FALLBACK_COLOR)
    return CurveAttributes(
        title=definition.title.localize(localizer),
        unit=parse_unit(definition.unit),
        color=parse_color(definition.color),
    )


def _prediction_attributes(
    metric_name: str,
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
) -> CurveAttributes | None:
    if metric_name in registered_metrics:
        return None
    if (predicted := _predicted_of(metric_name)) is None:
        return None
    predicted_metric_name, levels = predicted
    predicted_attributes = _declared_attributes(
        predicted_metric_name, localizer, registered_metrics
    )
    return CurveAttributes(
        title=localizer("Prediction of ") + predicted_attributes.title + localizer(levels),
        unit=predicted_attributes.unit,
        color=FALLBACK_COLOR,
    )


def metric_display_attributes(
    metric_name: str,
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
) -> CurveAttributes:
    if (
        prediction := _prediction_attributes(metric_name, localizer, registered_metrics)
    ) is not None:
        return prediction
    return _declared_attributes(metric_name, localizer, registered_metrics)
