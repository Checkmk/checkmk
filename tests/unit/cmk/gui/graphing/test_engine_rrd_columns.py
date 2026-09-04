#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics, Title, translations
from cmk.graphing_engine import ConsolidationFunction, MetricName, TimeRange, TimeSeries
from cmk.gui.graphing._engine_rrd_columns import merge_rrd_columns, rrd_column_names
from cmk.gui.utils.temperate_unit import TemperatureUnit

_CHECK_COMMAND = "check_mk-foo"

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


def _translations(
    specs: Mapping[str, translations.RenameTo | translations.ScaleBy],
) -> Sequence[translations.Translation]:
    return [
        translations.Translation(
            name="t",
            check_commands=[translations.PassiveCheck("foo")],
            translations=specs,
        )
    ]


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
