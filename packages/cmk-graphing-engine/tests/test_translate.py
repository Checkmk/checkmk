#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    MetricName,
    PerformanceData,
    PerformanceValue,
)
from cmk.graphing_engine._objects import MetricTranslation, RRDMetricData, RRDOriginal
from cmk.graphing_engine._translate import translate_performance_data


def test_translate_scales_value_and_scalars() -> None:
    perf = PerformanceData(
        check_command="check_mk-cpu",
        values=[
            PerformanceValue(
                metric_name=MetricName("cpu_user"),
                value=21.0,
                warning=40.0,
                critical=45.0,
                minimum=0.0,
                maximum=50.0,
            )
        ],
    )
    # Scale 2.0 must be applied to the value and every scalar bound.
    translations = {
        "check_mk-cpu": {
            MetricName("cpu_user"): MetricTranslation(name=MetricName("cpu_user"), scale=2.0)
        }
    }

    assert translate_performance_data(perf, translations) == {
        MetricName("cpu_user"): RRDMetricData(
            value=42.0,
            originals=[RRDOriginal(metric_name=MetricName("cpu_user"), scale=2.0)],
            warning=80.0,
            critical=90.0,
            minimum=0.0,
            maximum=100.0,
        )
    }


def test_translate_renames_metric_to_the_target() -> None:
    perf = PerformanceData(
        check_command="check_mk-sensor",
        values=[PerformanceValue(metric_name=MetricName("temperature"), value=20.0)],
    )
    translations = {
        "check_mk-sensor": {MetricName("temperature"): MetricTranslation(name=MetricName("temp"))}
    }

    assert translate_performance_data(perf, translations) == {
        MetricName("temp"): RRDMetricData(
            value=20.0,
            # The original keeps the raw (pre-rename) metric name.
            originals=[RRDOriginal(metric_name=MetricName("temperature"), scale=1.0)],
        )
    }


def test_translate_matches_regex_translation_entries() -> None:
    perf = PerformanceData(
        check_command="check_mk-if",
        values=[PerformanceValue(metric_name=MetricName("if_in_octets"), value=10.0)],
    )
    translations = {
        "check_mk-if": {MetricName("~if_.*_octets"): MetricTranslation(name=MetricName("cpu_user"))}
    }

    [(name, data)] = translate_performance_data(perf, translations).items()
    assert name == MetricName("cpu_user")
    assert data.originals == [RRDOriginal(metric_name=MetricName("if_in_octets"), scale=1.0)]


def test_translate_falls_back_for_unregistered_metric() -> None:
    perf = PerformanceData(
        check_command="",
        values=[PerformanceValue(metric_name=MetricName("unknown"), value=1.0)],
    )

    assert translate_performance_data(perf, {}) == {
        MetricName("unknown"): RRDMetricData(
            value=1.0,
            originals=[RRDOriginal(metric_name=MetricName("unknown"), scale=1.0)],
        )
    }


def test_translate_keeps_the_predict_prefix_on_the_renamed_metric() -> None:
    perf = PerformanceData(
        check_command="check_mk-sensor",
        values=[PerformanceValue(metric_name=MetricName("predict_temperature"), value=19.0)],
    )
    translations = {
        "check_mk-sensor": {MetricName("temperature"): MetricTranslation(name=MetricName("temp"))}
    }

    [(name, data)] = translate_performance_data(perf, translations).items()
    assert name == MetricName("predict_temp")
    assert data.originals == [RRDOriginal(metric_name=MetricName("predict_temperature"), scale=1.0)]


def test_translate_scales_a_predictive_metric_like_its_base() -> None:
    perf = PerformanceData(
        check_command="check_mk-cpu",
        values=[PerformanceValue(metric_name=MetricName("predict_cpu_user"), value=21.0)],
    )
    # The scale of the base metric (cpu_user) is applied to its predictive companion as well.
    translations = {
        "check_mk-cpu": {
            MetricName("cpu_user"): MetricTranslation(name=MetricName("cpu_user"), scale=2.0)
        }
    }

    [(name, data)] = translate_performance_data(perf, translations).items()
    assert name == MetricName("predict_cpu_user")
    assert data.value == 42.0
    assert data.originals == [RRDOriginal(metric_name=MetricName("predict_cpu_user"), scale=2.0)]


def test_translate_adds_the_deprecated_column_for_a_renamed_metric() -> None:
    # The service now emits the metric under its current name `temp`, but a translation renames the
    # deprecated `temperature` onto `temp`. The deprecated column is appended as a further original so a
    # graph spanning the rename keeps its historic segment.
    perf = PerformanceData(
        check_command="check_mk-sensor",
        values=[PerformanceValue(metric_name=MetricName("temp"), value=20.0)],
    )
    translations = {
        "check_mk-sensor": {MetricName("temperature"): MetricTranslation(name=MetricName("temp"))}
    }

    [(name, data)] = translate_performance_data(perf, translations).items()
    assert name == MetricName("temp")
    # Current column first (live data wins on overlap), the deprecated column appended.
    assert data.originals == [
        RRDOriginal(metric_name=MetricName("temp"), scale=1.0),
        RRDOriginal(metric_name=MetricName("temperature"), scale=1.0),
    ]


def test_translate_scales_the_deprecated_column_with_its_own_scale() -> None:
    perf = PerformanceData(
        check_command="check_mk-cpu",
        values=[PerformanceValue(metric_name=MetricName("cpu_user"), value=21.0)],
    )
    # `cpu_user_old` was renamed-and-scaled onto `cpu_user`; its historic column carries the old scale.
    translations = {
        "check_mk-cpu": {
            MetricName("cpu_user_old"): MetricTranslation(name=MetricName("cpu_user"), scale=2.0)
        }
    }

    [(name, data)] = translate_performance_data(perf, translations).items()
    assert name == MetricName("cpu_user")
    assert data.originals == [
        RRDOriginal(metric_name=MetricName("cpu_user"), scale=1.0),
        RRDOriginal(metric_name=MetricName("cpu_user_old"), scale=2.0),
    ]


def test_translate_does_not_reverse_translate_regex_entries() -> None:
    # A regex translation maps many names onto one and cannot be inverted, so no deprecated column is
    # added — only the current column remains.
    perf = PerformanceData(
        check_command="check_mk-if",
        values=[PerformanceValue(metric_name=MetricName("if_octets"), value=10.0)],
    )
    translations = {
        "check_mk-if": {MetricName("~if_.*"): MetricTranslation(name=MetricName("if_octets"))}
    }

    [(name, data)] = translate_performance_data(perf, translations).items()
    assert name == MetricName("if_octets")
    assert data.originals == [RRDOriginal(metric_name=MetricName("if_octets"), scale=1.0)]


def test_translate_adds_the_deprecated_column_with_the_predict_prefix() -> None:
    perf = PerformanceData(
        check_command="check_mk-sensor",
        values=[PerformanceValue(metric_name=MetricName("predict_temp"), value=19.0)],
    )
    translations = {
        "check_mk-sensor": {MetricName("temperature"): MetricTranslation(name=MetricName("temp"))}
    }

    [(name, data)] = translate_performance_data(perf, translations).items()
    assert name == MetricName("predict_temp")
    assert data.originals == [
        RRDOriginal(metric_name=MetricName("predict_temp"), scale=1.0),
        RRDOriginal(metric_name=MetricName("predict_temperature"), scale=1.0),
    ]


def test_translate_merges_metrics_renaming_to_the_same_target() -> None:
    perf = PerformanceData(
        check_command="check_mk-cpu",
        values=[
            PerformanceValue(metric_name=MetricName("user"), value=1.0),
            PerformanceValue(metric_name=MetricName("usr"), value=2.0),
        ],
    )
    translations = {
        "check_mk-cpu": {
            MetricName("user"): MetricTranslation(name=MetricName("cpu_user")),
            MetricName("usr"): MetricTranslation(name=MetricName("cpu_user")),
        }
    }

    [(name, data)] = translate_performance_data(perf, translations).items()
    assert name == MetricName("cpu_user")
    # The last contributing metric wins for the value; all originals are kept.
    assert data.value == 2.0
    assert data.originals == [
        RRDOriginal(metric_name=MetricName("user"), scale=1.0),
        RRDOriginal(metric_name=MetricName("usr"), scale=1.0),
    ]
