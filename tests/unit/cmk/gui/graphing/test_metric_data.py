#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics, Title, translations
from cmk.graphing_engine import (
    ConsolidationFunction,
    MetricName,
    TimeRange,
    TimeSeries,
)
from cmk.gui.graphing import (
    evaluated_metrics,
    EvaluatedMetric,
    merge_rrd_columns,
    rrd_column_names,
)
from cmk.gui.utils.temperature_unit import TemperatureUnit

# The check the translations below are registered for, as a passive check's performance data spells
# it and as the plug-in names it.
_CHECK_COMMAND = "check_mk-foo"
_CHECK_PLUGIN = "foo"

type _Specs = Mapping[
    str, translations.RenameTo | translations.ScaleBy | translations.RenameToAndScaleBy
]


def _translations(specs: _Specs) -> Sequence[translations.Translation]:
    return [
        translations.Translation(
            name="t",
            check_commands=[translations.PassiveCheck(_CHECK_PLUGIN)],
            translations=specs,
        )
    ]


_REGISTERED_METRICS: Mapping[str, metrics.Metric] = {
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


def _merged(
    rrd_columns: Sequence[tuple[str, Sequence[float | None] | None]],
    *,
    registered_translations: Sequence[translations.Translation] = (),
    temperature_unit: TemperatureUnit = TemperatureUnit.CELSIUS,
    target: str = "used",
) -> TimeSeries:
    return merge_rrd_columns(
        MetricName(target),
        rrd_columns,
        _CHECK_COMMAND,
        _REGISTERED_METRICS,
        registered_translations,
        temperature_unit=temperature_unit,
    )


def test_the_columns_of_a_metric_without_translations_are_its_own() -> None:
    assert list(rrd_column_names(MetricName("used"), ConsolidationFunction.MAX, 0, 300, [])) == [
        "rrddata:used:used.max:0:300:60"
    ]


def test_the_columns_of_a_metric_include_every_name_translated_to_it() -> None:
    assert sorted(
        rrd_column_names(
            MetricName("used"),
            ConsolidationFunction.MAX,
            0,
            300,
            _translations({"old": translations.RenameTo("used")}),
        )
    ) == ["rrddata:old:old.max:0:300:60", "rrddata:used:used.max:0:300:60"]


def test_merging_reads_the_grid_and_values_out_of_the_column() -> None:
    merged = _merged([("rrddata:used:used.max:0:300:60", [0, 180, 60, 1.0, 2.0, 3.0])])

    assert (merged.time_range, list(merged.values)) == (
        TimeRange(start=0, end=180, step=60),
        [1.0, 2.0, 3.0],
    )


def test_merging_drops_a_column_that_translates_to_another_metric() -> None:
    assert not _merged([("rrddata:other:other.max:0:300:60", [0, 180, 60, 1.0, 2.0, 3.0])]).values


def test_merging_scales_a_column_by_its_translation_factor() -> None:
    merged = _merged(
        [("rrddata:used:used.max:0:180:60", [0, 180, 60, 1.0, 2.0, 3.0])],
        registered_translations=_translations({"used": translations.ScaleBy(2.0)}),
    )

    assert list(merged.values) == [2.0, 4.0, 6.0]


def test_merging_takes_the_first_present_value_across_columns() -> None:
    merged = _merged(
        [
            ("rrddata:used:used.max:0:180:60", [0, 180, 60, None, 2.0, None]),
            ("rrddata:old:old.max:0:180:60", [0, 180, 60, 1.0, 9.0, None]),
        ],
        registered_translations=_translations({"old": translations.RenameTo("used")}),
    )

    assert list(merged.values) == [1.0, 2.0, None]


def test_merging_converts_to_the_users_temperature_unit() -> None:
    merged = _merged(
        [("rrddata:temp:temp.max:0:120:60", [0, 120, 60, 10.0, 20.0])],
        temperature_unit=TemperatureUnit.FAHRENHEIT,
        target="temp",
    )

    assert list(merged.values) == [50.0, 68.0]


def test_merging_skips_a_column_that_carries_no_values() -> None:
    assert not _merged([("rrddata:used:used.max:0:300:60", [0, 300, 60])]).values


def test_merging_rejects_the_none_a_nagios_core_answers_with() -> None:
    with pytest.raises(MKGeneralException):
        _merged([("rrddata:used:used.max:0:300:60", None)])


def _evaluated(
    perf_data_string: str,
    *,
    registered_translations: Sequence[translations.Translation] = (),
    temperature_unit: TemperatureUnit = TemperatureUnit.CELSIUS,
) -> Mapping[MetricName, EvaluatedMetric]:
    return evaluated_metrics(
        perf_data_string,
        _CHECK_COMMAND,
        registered_metrics=_REGISTERED_METRICS,
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


def test_a_temperature_metric_carries_its_already_converted_unit() -> None:
    unit_format = _evaluated("temp=10", temperature_unit=TemperatureUnit.FAHRENHEIT)[
        MetricName("temp")
    ].unit_format
    assert (unit_format.symbol, unit_format.convertible) == ("°F", False)


def test_a_pnp_suffix_names_the_check_command_the_translation_is_looked_up_with() -> None:
    # CMK-33772: perf data may carry a PNP-style "[check_command]" suffix. The suffix names the
    # command whose translations apply, not the outer service check command.
    evaluated = evaluated_metrics(
        "old=6.8;300;500 [check_mk-foo]",
        "check_mk-mrpe",
        registered_metrics=_REGISTERED_METRICS,
        registered_translations=_translations(
            {"old": translations.RenameToAndScaleBy("used", 0.001)}
        ),
        temperature_unit=TemperatureUnit.CELSIUS,
        debug=True,
    )

    assert [
        (name, metric.performance_data.value, metric.performance_data.warning)
        for name, metric in evaluated.items()
    ] == [(MetricName("used"), 0.0068, 0.3)]
