#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import perfometers as perfometers_v1
from cmk.graphing.v1 import Title
from cmk.graphing_engine import (
    AutoPrecision,
    CurveAttributes,
    DecimalNotation,
    EvaluatedBidirectional,
    EvaluatedFocusBound,
    EvaluatedFocusRange,
    EvaluatedPerfometer,
    EvaluatedSegment,
    EvaluatedStacked,
    FocusBoundKind,
    Unit,
)
from cmk.gui.graphing import (
    evaluated_perfometer,
    perfometer_label,
)
from cmk.gui.utils.temperature_unit import TemperatureUnit

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))


def _closed(value: float) -> EvaluatedFocusBound:
    return EvaluatedFocusBound(bound_kind=FocusBoundKind.CLOSED, value=value)


def _open(value: float) -> EvaluatedFocusBound:
    return EvaluatedFocusBound(bound_kind=FocusBoundKind.OPEN, value=value)


def _segment(value: float, color: str = "#111111", unit: Unit = _UNIT) -> EvaluatedSegment:
    return EvaluatedSegment(
        value=value, attributes=CurveAttributes(title="Segment", unit=unit, color=color)
    )


def _bar(
    *segments: EvaluatedSegment,
    lower: EvaluatedFocusBound | None = None,
    upper: EvaluatedFocusBound | None = None,
    name: str = "p",
) -> EvaluatedPerfometer:
    return EvaluatedPerfometer(
        name=name,
        focus_range=EvaluatedFocusRange(
            lower=lower if lower is not None else _closed(0.0),
            upper=upper if upper is not None else _closed(100.0),
        ),
        segments=list(segments),
    )


def test_label_of_a_bar_sums_its_segments() -> None:
    label = perfometer_label(_bar(_segment(30.0), _segment(12.0)), TemperatureUnit.CELSIUS)
    assert label == "42"


def test_label_of_a_bar_uses_the_first_segments_unit() -> None:
    percent = Unit(notation=DecimalNotation("%"), precision=AutoPrecision(2))
    label = perfometer_label(_bar(_segment(42.0, unit=percent)), TemperatureUnit.CELSIUS)
    assert label == "42 %"


def test_label_of_a_bidirectional_joins_both_halves() -> None:
    label = perfometer_label(
        EvaluatedBidirectional(
            name="both", left=_bar(_segment(1.0), name="l"), right=_bar(_segment(2.0), name="r")
        ),
        TemperatureUnit.CELSIUS,
    )
    assert label == "1 / 2"


def test_label_of_a_stacked_joins_upper_before_lower() -> None:
    label = perfometer_label(
        EvaluatedStacked(
            name="two", upper=_bar(_segment(1.0), name="up"), lower=_bar(_segment(2.0), name="lo")
        ),
        TemperatureUnit.CELSIUS,
    )
    assert label == "1 / 2"


def test_label_converts_to_the_users_temperature_unit() -> None:
    celsius = Unit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))
    bar = _bar(_segment(20.0, unit=celsius))
    assert perfometer_label(bar, TemperatureUnit.CELSIUS) == "20 °C"
    assert perfometer_label(bar, TemperatureUnit.FAHRENHEIT) == "68 °F"


def _time_bar(name: str) -> perfometers_v1.Perfometer:
    return perfometers_v1.Perfometer(
        name=name,
        focus_range=perfometers_v1.FocusRange(perfometers_v1.Closed(0), perfometers_v1.Open(100)),
        segments=[name],
    )


def _time_metric(name: str) -> metrics_v1.Metric:
    return metrics_v1.Metric(
        name=name,
        title=Title("Time"),
        unit=metrics_v1.Unit(metrics_v1.TimeNotation()),
        color=metrics_v1.Color.BLUE,
    )


def test_backup_age_draws_in_place_of_backup_size() -> None:
    evaluated = evaluated_perfometer(
        "backup_size=1000;;;; backup_age=10;;;;",
        "check_mk-veeam_backups",
        host_name="host",
        service_name="Backup job",
        registered_perfometers={name: _time_bar(name) for name in ("backup_size", "backup_age")},
        registered_metrics={name: _time_metric(name) for name in ("backup_size", "backup_age")},
        registered_translations=[],
        debug=True,
    )
    assert evaluated is not None
    assert evaluated.name == "backup_age"
