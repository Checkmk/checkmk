#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest

from cmk.gui.graphing._from_api import RegisteredMetric
from cmk.gui.graphing._legacy import check_metrics, CheckMetricEntry
from cmk.gui.graphing._translated_metrics import (
    _parse_check_command,
    find_matching_translation,
    lookup_metric_translations_for_check_command,
    parse_perf_data,
    ScalarBounds,
    translate_metrics,
    TranslationSpec,
)
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.type_defs import Perfdata, PerfDataTuple
from cmk.gui.unit_formatter import AutoPrecision
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils.metrics import MetricName


@pytest.mark.parametrize(
    "perf_str, check_command, result",
    [
        ("", None, ([], "")),
        (
            "he lo=1",
            None,
            (
                [
                    PerfDataTuple(metric_name="lo", lookup_metric_name="lo", value=1, unit_name=""),
                ],
                "",
            ),
        ),
        (
            "'há li'=2",
            None,
            (
                [
                    PerfDataTuple(
                        metric_name="há_li", lookup_metric_name="há_li", value=2, unit_name=""
                    ),
                ],
                "",
            ),
        ),
        (
            "hé ßß=3",
            None,
            (
                [
                    PerfDataTuple(metric_name="ßß", lookup_metric_name="ßß", value=3, unit_name=""),
                ],
                "",
            ),
        ),
        (
            "hi=6 [ihe]",
            "ter",
            (
                [
                    PerfDataTuple(metric_name="hi", lookup_metric_name="hi", value=6, unit_name=""),
                ],
                "ihe",
            ),
        ),
        ("hi=l6 [ihe]", "ter", ([], "ihe")),
        (
            "hi=6 [ihe]",
            "ter",
            (
                [
                    PerfDataTuple(metric_name="hi", lookup_metric_name="hi", value=6, unit_name=""),
                ],
                "ihe",
            ),
        ),
        (
            "hi=5 no=6",
            "test",
            (
                [
                    PerfDataTuple(metric_name="hi", lookup_metric_name="hi", value=5, unit_name=""),
                    PerfDataTuple(metric_name="no", lookup_metric_name="no", value=6, unit_name=""),
                ],
                "test",
            ),
        ),
        (
            "hi=5;6;7;8;9 'not here'=6;5.6;;;",
            "test",
            (
                [
                    PerfDataTuple(
                        metric_name="hi",
                        lookup_metric_name="hi",
                        value=5,
                        unit_name="",
                        warn=6,
                        crit=7,
                        min_=8,
                        max_=9,
                    ),
                    PerfDataTuple(
                        metric_name="not_here",
                        lookup_metric_name="not_here",
                        value=6,
                        unit_name="",
                        warn=5.6,
                    ),
                ],
                "test",
            ),
        ),
        (
            "hi=5G;;;; 'not here'=6M;5.6;;;",
            "test",
            (
                [
                    PerfDataTuple(
                        metric_name="hi", lookup_metric_name="hi", value=5, unit_name="G"
                    ),
                    PerfDataTuple(
                        metric_name="not_here",
                        lookup_metric_name="not_here",
                        value=6,
                        unit_name="M",
                        warn=5.6,
                    ),
                ],
                "test",
            ),
        ),
        (
            "11.26=6;;;;",
            "check_mk-local",
            (
                [
                    PerfDataTuple(
                        metric_name="11.26", lookup_metric_name="11.26", value=6, unit_name=""
                    ),
                ],
                "check_mk-local",
            ),
        ),
    ],
)
def test_parse_perf_data(
    perf_str: str,
    check_command: str | None,
    result: tuple[Perfdata, str],
) -> None:
    assert parse_perf_data(perf_str, check_command, debug=False) == result


def test_parse_perf_data2() -> None:
    with pytest.raises(ValueError):
        parse_perf_data("hi ho", None, debug=True)


@pytest.mark.parametrize(
    "perf_name, check_command, expected_translation_spec",
    [
        (
            "in",
            "check_mk-lnx_if",
            TranslationSpec(
                name="if_in_bps",
                scale=8,
                auto_graph=True,
                deprecated="",
            ),
        ),
        (
            "memused",
            "check_mk-hr_mem",
            TranslationSpec(
                name="mem_lnx_total_used",
                scale=1024**2,
                auto_graph=True,
                deprecated="",
            ),
        ),
        (
            "fake",
            "check_mk-imaginary",
            TranslationSpec(
                name="fake",
                scale=1.0,
                auto_graph=True,
                deprecated="",
            ),
        ),
        # CMK-33772: NagiosPlugin("check_ping.exe") and NagiosPlugin("check_tcp.exe")
        # are registered by werk #16254. parse_perf_data normalizes the lookup key
        # via .replace(".", "_"), so the registration must use the same key form.
        (
            "rta",
            "check_ping_exe",
            TranslationSpec(
                # ~.*rta is a regex entry — the spec keeps the original key as
                # the name. What matters here is the scale being 0.001.
                name="~.*rta",
                scale=0.001,
                auto_graph=True,
                deprecated="",
            ),
        ),
        (
            "time",
            "check_tcp_exe",
            TranslationSpec(
                name="response_time",
                scale=1.0,
                auto_graph=True,
                deprecated="",
            ),
        ),
    ],
)
def test_perfvar_translation(
    perf_name: str, check_command: str, expected_translation_spec: TranslationSpec
) -> None:
    assert (
        find_matching_translation(
            MetricName(perf_name),
            lookup_metric_translations_for_check_command(check_metrics, check_command),
        )
        == expected_translation_spec
    )


@pytest.mark.parametrize(
    ["translations", "expected_result"],
    [
        pytest.param(
            {},
            TranslationSpec(
                name=MetricName("my_metric"),
                scale=1.0,
                auto_graph=True,
                deprecated="",
            ),
            id="no translations",
        ),
        pytest.param(
            {
                MetricName("old_name"): TranslationSpec(
                    name=MetricName("new_name"),
                    scale=1.0,
                    auto_graph=True,
                    deprecated="",
                )
            },
            TranslationSpec(
                name=MetricName("my_metric"),
                scale=1.0,
                auto_graph=True,
                deprecated="",
            ),
            id="no applicable translations",
        ),
        pytest.param(
            {
                MetricName("my_metric"): TranslationSpec(
                    name=MetricName("new_name"),
                    scale=2.0,
                    auto_graph=True,
                    deprecated="",
                ),
                MetricName("other_metric"): TranslationSpec(
                    name=MetricName("other_new_name"),
                    scale=0.1,
                    auto_graph=True,
                    deprecated="",
                ),
            },
            TranslationSpec(
                name=MetricName("new_name"),
                scale=2.0,
                auto_graph=True,
                deprecated="",
            ),
            id="1-to-1 translations",
        ),
        pytest.param(
            {
                MetricName("~.*my_metric"): TranslationSpec(
                    name=MetricName("~.*my_metric"),
                    scale=5.0,
                    auto_graph=True,
                    deprecated="",
                ),
                MetricName("other_metric"): TranslationSpec(
                    name=MetricName("other_new_name"),
                    scale=0.1,
                    auto_graph=True,
                    deprecated="",
                ),
            },
            TranslationSpec(
                name=MetricName("~.*my_metric"),
                scale=5.0,
                auto_graph=True,
                deprecated="",
            ),
            id="regex translations",
        ),
    ],
)
def test_find_matching_translation(
    translations: Mapping[MetricName, TranslationSpec],
    expected_result: TranslationSpec,
) -> None:
    assert find_matching_translation(MetricName("my_metric"), translations) == expected_result


@pytest.mark.parametrize(
    "metric_name, predictive_metric_name, expected_title, expected_color",
    [
        pytest.param(
            "messages_outbound",
            "predict_messages_outbound",
            "Prediction of Outbound messages (upper levels)",
            "#4b4b4b",
            id="upper",
        ),
        pytest.param(
            "messages_outbound",
            "predict_lower_messages_outbound",
            "Prediction of Outbound messages (lower levels)",
            "#4b4b4b",
            id="lower",
        ),
    ],
)
def test_translate_metrics_with_predictive_metrics(
    metric_name: str,
    predictive_metric_name: str,
    expected_title: str,
    expected_color: str,
) -> None:
    perfdata: Perfdata = [
        PerfDataTuple(
            metric_name=metric_name, lookup_metric_name=metric_name, value=0, unit_name=""
        ),
        PerfDataTuple(
            metric_name=predictive_metric_name,
            lookup_metric_name=metric_name,
            value=0,
            unit_name="",
        ),
    ]
    translated_metrics = translate_metrics(
        perfdata,
        "my-check-plugin",
        {
            "messages_outbound": RegisteredMetric(
                name="messages_outbound",
                title_localizer=lambda _localizer: "Outbound messages",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol="/s"),
                    precision=AutoPrecision(digits=2),
                ),
                color="",
            )
        },
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert translated_metrics[predictive_metric_name].title == expected_title
    assert (
        translated_metrics[predictive_metric_name].unit_spec
        == translated_metrics[metric_name].unit_spec
    )
    assert translated_metrics[predictive_metric_name].color == expected_color


def test_translate_metrics_with_multiple_predictive_metrics() -> None:
    perfdata: Perfdata = [
        PerfDataTuple(
            metric_name="messages_outbound",
            lookup_metric_name="messages_outbound",
            value=0,
            unit_name="",
        ),
        PerfDataTuple(
            metric_name="predict_messages_outbound",
            lookup_metric_name="messages_outbound",
            value=0,
            unit_name="",
        ),
        PerfDataTuple(
            metric_name="predict_lower_messages_outbound",
            lookup_metric_name="messages_outbound",
            value=0,
            unit_name="",
        ),
    ]
    translated_metrics = translate_metrics(
        perfdata,
        "my-check-plugin",
        {},
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert translated_metrics["predict_messages_outbound"].color == "#4b4b4b"
    assert translated_metrics["predict_lower_messages_outbound"].color == "#5a5a5a"


@pytest.mark.parametrize(
    ["default_temperature_unit", "expected_value", "expected_scalars"],
    [
        pytest.param(
            TemperatureUnit.CELSIUS,
            59.05,
            ScalarBounds(warn=85.05, crit=85.05),
            id="no unit conversion",
        ),
        pytest.param(
            TemperatureUnit.FAHRENHEIT,
            138.29,
            ScalarBounds(warn=185.09, crit=185.09),
            id="with unit conversion",
        ),
    ],
)
def test_translate_metrics(
    default_temperature_unit: TemperatureUnit,
    expected_value: float,
    expected_scalars: ScalarBounds,
) -> None:
    translated_metric = translate_metrics(
        [
            PerfDataTuple(
                metric_name="temp",
                lookup_metric_name="temp",
                value=59.05,
                unit_name="",
                warn=85.05,
                crit=85.05,
            )
        ],
        "check_mk-lnx_thermal",
        {
            "temp": RegisteredMetric(
                name="temp",
                title_localizer=lambda _localizer: "Temperature",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol="°C"),
                    precision=AutoPrecision(digits=2),
                ),
                color="",
            )
        },
        temperature_unit=default_temperature_unit,
    )["temp"]
    assert translated_metric.value == expected_value
    assert translated_metric.scalar == expected_scalars


@pytest.mark.parametrize(
    ["translations", "check_command", "expected_result"],
    [
        pytest.param(
            {},
            "check_mk-x",
            {},
            id="no matching entry",
        ),
        pytest.param(
            {
                "check_mk-x": {MetricName("old"): {"name": MetricName("new")}},
                "check_mk-y": {MetricName("a"): {"scale": 2}},
            },
            "check_mk-x",
            {
                MetricName("old"): TranslationSpec(
                    name=MetricName("new"),
                    scale=1.0,
                    auto_graph=True,
                    deprecated="",
                )
            },
            id="standard check",
        ),
        pytest.param(
            {
                "check_mk-x": {MetricName("old"): {"name": MetricName("new")}},
                "check_mk-y": {MetricName("a"): {"scale": 2}},
            },
            "check_mk-mgmt_x",
            {
                MetricName("old"): TranslationSpec(
                    name=MetricName("new"),
                    scale=1.0,
                    auto_graph=True,
                    deprecated="",
                )
            },
            id="management board, fallback to standard check",
        ),
        pytest.param(
            {
                "check_mk_x": {MetricName("old"): {"name": MetricName("new")}},
                "check_mk-mgmt_x": {MetricName("old"): {"scale": 3}},
            },
            "check_mk-mgmt_x",
            {
                MetricName("old"): TranslationSpec(
                    name="old",
                    scale=3,
                    auto_graph=True,
                    deprecated="",
                )
            },
            id="management board, explicit entry",
        ),
        pytest.param(
            {
                "check_mk-x": {MetricName("old"): {"name": MetricName("new")}},
                "check_mk-y": {MetricName("a"): {"scale": 2}},
            },
            None,
            {},
            id="no check command",
        ),
    ],
)
def test_lookup_metric_translations_for_check_command(
    translations: Mapping[str, Mapping[MetricName, CheckMetricEntry]],
    check_command: str | None,
    expected_result: Mapping[MetricName, TranslationSpec],
) -> None:
    metric_translations = lookup_metric_translations_for_check_command(translations, check_command)
    assert metric_translations == expected_result


@pytest.mark.parametrize(
    "check_command, expected",
    [
        pytest.param(
            "check-mk-custom!foobar",
            "check-mk-custom",
            id="custom-foobar",
        ),
        pytest.param(
            "check-mk-custom!check_ping",
            "check_ping",
            id="custom-check_ping",
        ),
        pytest.param(
            "check-mk-custom!./check_ping",
            "check_ping",
            id="custom-check_ping-2",
        ),
    ],
)
def test__parse_check_command(check_command: str, expected: str) -> None:
    assert _parse_check_command(check_command) == expected
