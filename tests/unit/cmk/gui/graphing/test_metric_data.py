#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics, Title, translations
from cmk.graphing_engine import (
    ConsolidationFunction,
    HostName,
    MetricName,
    RRDMetric,
    ServiceName,
    TimeRange,
    TimeSeries,
)
from cmk.gui.graphing._metric_data import (
    chop_last_empty_step,
    evaluated_metrics,
    EvaluatedMetric,
    map_metric_names,
    merge_rrd_columns,
    merge_series,
    parse_performance_data,
    RawPerformanceData,
    RawPerformanceValue,
    resample,
    reverse_translated_names,
    rrd_column_names,
    rrd_originals,
    RRDOriginal,
    scaled_series,
    translate_metric_names,
    translate_performance_data,
)
from cmk.gui.utils.temperate_unit import TemperatureUnit


def test_parse_performance_data_merges_rrd_only_metrics() -> None:
    # Legacy reads the livestatus "metrics" column too, so a metric present in RRD but absent from
    # the live perf_data string still shows up (as a synthetic value=1 entry, deduplicated).
    parsed = parse_performance_data("live=5", "check_mk-foo", ["live", "rrd_only"], debug=False)
    by_name = {name: value.value for name, value in parsed.values.items()}
    assert by_name == {"live": 5.0, "rrd_only": 1.0}


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


def _raw(values: Mapping[str, RawPerformanceValue]) -> RawPerformanceData:
    return RawPerformanceData(
        check_command=_CHECK_COMMAND,
        values={MetricName(name): value for name, value in values.items()},
    )


def _original(name: str, scale: float) -> RRDOriginal:
    return RRDOriginal(metric_name=MetricName(name), scale=scale)


def test_map_metric_names_pairs_raw_names_with_their_canonical_names() -> None:
    # A set of canonical names cannot say which raw column produced which name; the mapping can. A
    # raw name no translation renames is its own canonical name, so no raw name is dropped.
    assert dict(
        map_metric_names(
            _CHECK_COMMAND,
            [MetricName("old"), MetricName("untouched")],
            _translations({"old": translations.RenameTo("new")}),
        )
    ) == {MetricName("old"): MetricName("new"), MetricName("untouched"): MetricName("untouched")}


def test_two_raw_names_sharing_a_canonical_name_keep_their_own_entries() -> None:
    # The case the frozenset cannot express at all: it reports one name where two columns exist, so
    # a caller reading it back has no way to tell which of them it may ask an RRD for.
    assert dict(
        map_metric_names(
            _CHECK_COMMAND,
            [MetricName("if_in_octets"), MetricName("if_out_octets")],
            _translations({"~if_.*_octets": translations.RenameTo("if_octets")}),
        )
    ) == {
        MetricName("if_in_octets"): MetricName("if_octets"),
        MetricName("if_out_octets"): MetricName("if_octets"),
    }


def test_a_scaling_translation_leaves_the_name_alone() -> None:
    # A translation that only scales is still a translation, and a caller that resolves a name
    # through the mapping has to get the raw name back rather than nothing.
    assert dict(
        map_metric_names(
            _CHECK_COMMAND,
            [MetricName("mem")],
            _translations({"mem": translations.ScaleBy(1024)}),
        )
    ) == {MetricName("mem"): MetricName("mem")}


def test_metric_names_are_reported_under_their_canonical_name() -> None:
    assert translate_metric_names(
        _CHECK_COMMAND,
        [MetricName("old"), MetricName("untouched")],
        _translations({"old": translations.RenameTo("new")}),
    ) == {MetricName("new"), MetricName("untouched")}


def test_a_predictive_metric_keeps_its_prefix_while_its_base_is_renamed() -> None:
    # The prediction of a renamed metric is stored under the prefixed old name, so the prefix has to
    # survive the rename rather than being translated as part of the name.
    assert translate_metric_names(
        _CHECK_COMMAND,
        [MetricName("predict_old"), MetricName("predict_lower_old")],
        _translations({"old": translations.RenameTo("new")}),
    ) == {MetricName("predict_new"), MetricName("predict_lower_new")}


def test_a_regex_translation_matches_by_pattern() -> None:
    assert translate_metric_names(
        _CHECK_COMMAND,
        [MetricName("if_out_octets")],
        _translations({"~if_.*_octets": translations.RenameTo("if_octets")}),
    ) == {MetricName("if_octets")}


def test_an_unregistered_check_command_translates_nothing() -> None:
    assert translate_metric_names(
        "check_mk-other",
        [MetricName("old")],
        _translations({"old": translations.RenameTo("new")}),
    ) == {MetricName("old")}


def test_a_scaling_translation_scales_the_value_and_every_threshold() -> None:
    [(name, data)] = translate_performance_data(
        _CHECK_COMMAND,
        {
            MetricName("x"): RawPerformanceValue(
                value=5.0,
                warning=7.0,
                critical=9.0,
                lower_warning=3.0,
                lower_critical=1.0,
                minimum=0.0,
                maximum=10.0,
            )
        },
        _translations({"x": translations.ScaleBy(1024)}),
    ).items()
    assert name == MetricName("x")
    assert (data.value, data.warning, data.critical) == (5120.0, 7168.0, 9216.0)
    assert (data.lower_warning, data.lower_critical) == (3072.0, 1024.0)
    assert (data.minimum, data.maximum) == (0.0, 10240.0)


def test_an_absent_threshold_stays_absent_when_scaled() -> None:
    [(_name, data)] = translate_performance_data(
        _CHECK_COMMAND,
        {MetricName("x"): RawPerformanceValue(value=5.0)},
        _translations({"x": translations.ScaleBy(1024)}),
    ).items()
    assert data.warning is None
    assert data.maximum is None


def test_a_metric_is_drawn_from_the_column_its_data_was_translated_from() -> None:
    # The canonical name has no RRD of its own here: the series comes from the column the performance
    # data carried, and it carries the factor the value was scaled by.
    assert rrd_originals(
        MetricName("new"),
        _raw({"old": RawPerformanceValue(value=5.0)}),
        _translations({"old": translations.RenameToAndScaleBy("new", 1000)}),
    ) == [_original("old", 1000.0)]


def test_two_columns_translated_onto_one_metric_are_both_drawn() -> None:
    assert rrd_originals(
        MetricName("m"),
        _raw({"a": RawPerformanceValue(value=1.0), "b": RawPerformanceValue(value=2.0)}),
        _translations({"a": translations.RenameTo("m"), "b": translations.RenameTo("m")}),
    ) == [_original("a", 1.0), _original("b", 1.0)]


def test_a_deprecated_column_absent_from_the_performance_data_is_still_drawn() -> None:
    # The old column is gone from the performance data but its RRD may still be around, so it is read
    # alongside the current one - scaled by the translation that renamed it.
    assert rrd_originals(
        MetricName("new"),
        _raw({"new": RawPerformanceValue(value=5.0)}),
        _translations({"old": translations.RenameToAndScaleBy("new", 1000)}),
    ) == [_original("new", 1.0), _original("old", 1000.0)]


def test_a_metric_without_performance_data_falls_back_to_its_own_column_unscaled() -> None:
    assert rrd_originals(
        MetricName("y"),
        _raw({"x": RawPerformanceValue(value=5.0)}),
        _translations({"x": translations.ScaleBy(1024)}),
    ) == [_original("y", 1.0)]


def test_reverse_translated_names_always_contains_the_metric_itself() -> None:
    assert reverse_translated_names(MetricName("new"), []) == {MetricName("new")}


def test_reverse_translated_names_collects_every_name_renamed_to_it() -> None:
    assert reverse_translated_names(
        MetricName("new"),
        [
            *_translations({"old": translations.RenameTo("new")}),
            *_translations({"ancient": translations.RenameToAndScaleBy("new", 2.0)}),
        ],
    ) == {MetricName("new"), MetricName("old"), MetricName("ancient")}


def test_reverse_translated_names_skips_a_regex_translation() -> None:
    # "~.*rta" maps many raw names onto one canonical name, so it cannot be reversed.
    assert reverse_translated_names(
        MetricName("rta"), _translations({"~.*rta": translations.RenameTo("rta")})
    ) == {MetricName("rta")}


def test_reverse_translated_names_ignores_a_translation_to_another_metric() -> None:
    assert reverse_translated_names(
        MetricName("new"), _translations({"old": translations.RenameTo("other")})
    ) == {MetricName("new")}


_METRIC = RRDMetric(
    host_name=HostName("h"), service_name=ServiceName("svc"), metric_name=MetricName("x")
)


def _series(start: int, end: int, step: int, values: Sequence[float | None]) -> TimeSeries:
    return TimeSeries(time_range=TimeRange(start=start, end=end, step=step), values=values)


def test_a_series_already_on_the_grid_is_handed_back_unchanged() -> None:
    series = _series(0, 30, 10, [1.0, 2.0, 3.0])
    assert resample(series, series.time_range, ConsolidationFunction.MAX) is series


def test_a_coarser_grid_folds_each_bucket_with_the_consolidation_function() -> None:
    series = _series(0, 60, 10, [1.0, 5.0, 2.0, 6.0, 3.0, 7.0])
    coarse = TimeRange(start=0, end=60, step=30)
    assert list(resample(series, coarse, ConsolidationFunction.MAX).values) == [5.0, 7.0]
    assert list(resample(series, coarse, ConsolidationFunction.MIN).values) == [1.0, 3.0]
    assert list(resample(series, coarse, ConsolidationFunction.AVERAGE).values) == [
        8.0 / 3.0,
        16.0 / 3.0,
    ]


def test_a_bucket_without_a_single_value_folds_to_a_gap() -> None:
    series = _series(0, 60, 10, [1.0, 5.0, 2.0, None, None, None])
    resampled = resample(series, TimeRange(start=0, end=60, step=30), ConsolidationFunction.MAX)
    assert list(resampled.values) == [5.0, None]


def test_a_finer_grid_forward_fills_the_points_it_has() -> None:
    series = _series(0, 60, 30, [1.0, 2.0])
    resampled = resample(series, TimeRange(start=0, end=60, step=10), ConsolidationFunction.MAX)
    assert list(resampled.values) == [1.0, 1.0, 1.0, 2.0, 2.0, 2.0]


def test_an_empty_series_becomes_a_gap_on_the_requested_grid() -> None:
    resampled = resample(
        _series(0, 30, 10, []), TimeRange(start=0, end=60, step=20), ConsolidationFunction.MAX
    )
    assert list(resampled.values) == [None, None, None]


def test_scaling_multiplies_the_present_values_and_keeps_the_gaps() -> None:
    scaled = scaled_series(_series(0, 30, 10, [1.0, None, 3.0]), 1024)
    assert list(scaled.values) == [1024.0, None, 3072.0]


def test_scaling_by_one_hands_the_series_back_unchanged() -> None:
    series = _series(0, 30, 10, [1.0, 2.0, 3.0])
    assert scaled_series(series, 1.0) is series


def test_merging_takes_the_first_series_that_has_a_value_at_a_point() -> None:
    merged = merge_series(
        [_series(0, 30, 10, [None, 2.0, None]), _series(0, 30, 10, [9.0, 9.0, 9.0])],
        TimeRange(start=0, end=30, step=10),
    )
    assert list(merged.values) == [9.0, 2.0, 9.0]


def test_the_empty_trailing_step_of_a_graph_ending_now_is_dropped() -> None:
    # The current RRD step has no data yet, so an all-None last point is stripped rather than drawn as
    # a gap. "Now" is what makes it the current step, hence the clock.
    end = int(time.time())
    chopped = chop_last_empty_step({_METRIC: _series(end - 30, end, 10, [1.0, 2.0, None])}, end)
    assert list(chopped[_METRIC].values) == [1.0, 2.0]
    assert chopped[_METRIC].time_range == TimeRange(start=end - 30, end=end - 10, step=10)


def test_a_trailing_gap_in_the_past_is_kept() -> None:
    # Well before "now" an all-None last point is real missing data, not a step that has yet to fill.
    time_series = {_METRIC: _series(0, 30, 10, [1.0, 2.0, None])}
    assert chop_last_empty_step(time_series, 30) == time_series


def test_a_step_one_curve_still_has_data_for_is_kept() -> None:
    end = int(time.time())
    other = RRDMetric(
        host_name=HostName("h"), service_name=ServiceName("svc"), metric_name=MetricName("y")
    )
    time_series = {
        _METRIC: _series(end - 30, end, 10, [1.0, 2.0, None]),
        other: _series(end - 30, end, 10, [1.0, 2.0, 3.0]),
    }
    assert chop_last_empty_step(time_series, end) == time_series


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
    rrd_metrics: Sequence[MetricName] = (),
    registered_translations: Sequence[translations.Translation] = (),
    temperature_unit: TemperatureUnit = TemperatureUnit.CELSIUS,
) -> Mapping[MetricName, EvaluatedMetric]:
    return evaluated_metrics(
        perf_data_string,
        _CHECK_COMMAND,
        rrd_metrics,
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


def test_a_metric_only_the_rrd_knows_is_read_as_well() -> None:
    evaluated = _evaluated("used=10B", rrd_metrics=[MetricName("temp")])
    assert sorted(evaluated) == [MetricName("temp"), MetricName("used")]


def test_performance_data_wins_over_what_the_rrd_reports() -> None:
    evaluated = _evaluated("used=10B", rrd_metrics=[MetricName("used")])
    assert evaluated[MetricName("used")].performance_data.value == 10.0


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
