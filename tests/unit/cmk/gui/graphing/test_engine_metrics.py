#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing.v1 import metrics, Title, translations
from cmk.graphing_engine import MetricName
from cmk.gui.graphing._engine_metrics import evaluated_metrics, EvaluatedMetric
from cmk.gui.utils.temperate_unit import TemperatureUnit

_CHECK_COMMAND = "check_mk-foo"
_CHECK_PLUGIN = "foo"

_REGISTERED = {
    "used": metrics.Metric(
        name="used",
        title=Title("Used"),
        unit=metrics.Unit(metrics.SINotation("B")),
        color=metrics.Color.BLUE,
    ),
    "temp": metrics.Metric(
        name="temp",
        title=Title("Temperature"),
        unit=metrics.Unit(metrics.DecimalNotation("°C")),
        color=metrics.Color.ORANGE,
    ),
}


def _translations(
    specs: Mapping[str, translations.RenameTo | translations.ScaleBy],
) -> Sequence[translations.Translation]:
    return [
        translations.Translation(
            name="t",
            check_commands=[translations.PassiveCheck(_CHECK_PLUGIN)],
            translations=specs,
        )
    ]


def _evaluated(
    perf_data_string: str,
    *,
    rrd_metrics: Sequence[MetricName] = (),
    registered_translations: Sequence[translations.Translation] = (),
    temperature_unit: TemperatureUnit = TemperatureUnit.CELSIUS,
) -> Mapping[MetricName, EvaluatedMetric]:
    return evaluated_metrics(
        perf_data_string,
        _CHECK_COMMAND,
        rrd_metrics,
        registered_metrics=_REGISTERED,
        registered_translations=registered_translations,
        temperature_unit=temperature_unit,
        debug=True,
    )


def test_a_registered_metric_is_read_with_its_declared_display() -> None:
    evaluated = _evaluated("used=10B")[MetricName("used")]
    assert (evaluated.name, evaluated.title, evaluated.color, evaluated.formatter.symbol) == (
        MetricName("used"),
        "Used",
        "#28a2f3",
        "B",
    )


def test_a_registered_metric_carries_its_value_and_every_scalar() -> None:
    performance_data = _evaluated("used=10B;20;30;0;100")[MetricName("used")].performance_data
    assert (
        performance_data.value,
        performance_data.warning,
        performance_data.critical,
        performance_data.minimum,
        performance_data.maximum,
    ) == (10.0, 20.0, 30.0, 0.0, 100.0)


def test_an_unregistered_metric_falls_back_to_its_name_and_the_fallback_colour() -> None:
    evaluated = _evaluated("unknown=10")[MetricName("unknown")]
    assert (evaluated.title, evaluated.color) == ("unknown", "#8c8c8c")


def test_a_renaming_translation_moves_a_metric_to_its_canonical_name() -> None:
    evaluated = _evaluated(
        "old=10B", registered_translations=_translations({"old": translations.RenameTo("used")})
    )
    assert [(name, metric.title) for name, metric in evaluated.items()] == [
        (MetricName("used"), "Used")
    ]


def test_a_scaling_translation_scales_the_value_and_every_scalar() -> None:
    performance_data = _evaluated(
        "used=10;20;30;0;100",
        registered_translations=_translations({"used": translations.ScaleBy(2.0)}),
    )[MetricName("used")].performance_data
    assert (
        performance_data.value,
        performance_data.warning,
        performance_data.critical,
        performance_data.minimum,
        performance_data.maximum,
    ) == (20.0, 40.0, 60.0, 0.0, 200.0)


def test_a_temperature_metric_is_converted_to_the_users_unit() -> None:
    performance_data = _evaluated("temp=10;20", temperature_unit=TemperatureUnit.FAHRENHEIT)[
        MetricName("temp")
    ].performance_data
    assert (performance_data.value, performance_data.warning) == (50.0, 68.0)


def test_a_metric_only_the_rrd_knows_is_read_as_well() -> None:
    evaluated = _evaluated("used=10B", rrd_metrics=[MetricName("temp")])
    assert sorted(evaluated) == [MetricName("temp"), MetricName("used")]


def test_performance_data_wins_over_what_the_rrd_reports() -> None:
    evaluated = _evaluated("used=10B", rrd_metrics=[MetricName("used")])
    assert evaluated[MetricName("used")].performance_data.value == 10.0
