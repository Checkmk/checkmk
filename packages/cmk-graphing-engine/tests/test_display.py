#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.graphing.v1 import metrics, Title
from cmk.graphing_engine import metric_display_attributes
from cmk.graphing_engine._display import FALLBACK_COLOR

_REGISTERED: Mapping[str, metrics.Metric] = {
    "used": metrics.Metric(
        name="used",
        title=Title("Used"),
        unit=metrics.Unit(metrics.SINotation("B")),
        color=metrics.Color.BLUE,
    ),
    "predict_declared": metrics.Metric(
        name="predict_declared",
        title=Title("A metric that happens to be named like a prediction"),
        unit=metrics.Unit(metrics.SINotation("s")),
        color=metrics.Color.GREEN,
    ),
    "declared": metrics.Metric(
        name="declared",
        title=Title("Declared"),
        unit=metrics.Unit(metrics.SINotation("B")),
        color=metrics.Color.BLUE,
    ),
}


def _attributes(metric_name: str) -> tuple[str, str, str]:
    attributes = metric_display_attributes(metric_name, lambda text: text, _REGISTERED)
    return attributes.title, attributes.unit.notation.symbol, attributes.color


def test_a_registered_metric_is_read_from_its_declaration() -> None:
    assert _attributes("used") == ("Used", "B", "#28a2f3")


def test_an_unregistered_metric_falls_back_to_its_name() -> None:
    assert _attributes("unknown") == ("unknown", "", FALLBACK_COLOR)


def test_an_upper_prediction_is_titled_after_the_metric_it_predicts() -> None:
    assert _attributes("predict_used") == ("Prediction of Used (upper levels)", "B", FALLBACK_COLOR)


def test_a_lower_prediction_is_titled_after_the_metric_it_predicts() -> None:
    assert _attributes("predict_lower_used") == (
        "Prediction of Used (lower levels)",
        "B",
        FALLBACK_COLOR,
    )


def test_a_prediction_of_an_unregistered_metric_keeps_the_bare_name() -> None:
    assert _attributes("predict_unknown") == (
        "Prediction of unknown (upper levels)",
        "",
        FALLBACK_COLOR,
    )


def test_a_declared_metric_named_like_a_prediction_keeps_its_own_declaration() -> None:
    assert _attributes("predict_declared") == (
        "A metric that happens to be named like a prediction",
        "s",
        "#15d1a0",
    )
