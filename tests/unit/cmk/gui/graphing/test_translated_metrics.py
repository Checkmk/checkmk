#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest

from cmk.gui.config import active_config
from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._from_api import RegisteredMetric
from cmk.gui.graphing._legacy import check_metrics, CheckMetricEntry
from cmk.gui.graphing._translated_metrics import (
    _parse_check_command,
    find_matching_translation,
    lookup_metric_translations_for_check_command,
    parse_perf_data,
    translate_metrics,
    TranslationSpec,
)
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.type_defs import Perfdata, PerfDataTuple
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils.metrics import MetricName

from tests.unit.cmk.web_test_app import SetConfig


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "perf_str, check_command, result",
    [
        ("", None, ([], "")),
        (
            "he lo=1",
            None,
            (
                [
                    PerfDataTuple("lo", "lo", 1, "", None, None, None, None),
                ],
                "",
            ),
        ),
        (
            "'há li'=2",
            None,
            (
                [
                    PerfDataTuple("há_li", "há_li", 2, "", None, None, None, None),
                ],
                "",
            ),
        ),
        (
            "hé ßß=3",
            None,
            (
                [
                    PerfDataTuple("ßß", "ßß", 3, "", None, None, None, None),
                ],
                "",
            ),
        ),
        (
            "hi=6 [ihe]",
            "ter",
            (
                [
                    PerfDataTuple("hi", "hi", 6, "", None, None, None, None),
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
                    PerfDataTuple("hi", "hi", 6, "", None, None, None, None),
                ],
                "ihe",
            ),
        ),
        (
            "hi=5 no=6",
            "test",
            (
                [
                    PerfDataTuple("hi", "hi", 5, "", None, None, None, None),
                    PerfDataTuple("no", "no", 6, "", None, None, None, None),
                ],
                "test",
            ),
        ),
        (
            "hi=5;6;7;8;9 'not here'=6;5.6;;;",
            "test",
            (
                [
                    PerfDataTuple("hi", "hi", 5, "", 6, 7, 8, 9),
                    PerfDataTuple("not_here", "not_here", 6, "", 5.6, None, None, None),
                ],
                "test",
            ),
        ),
        (
            "hi=5G;;;; 'not here'=6M;5.6;;;",
            "test",
            (
                [
                    PerfDataTuple("hi", "hi", 5, "G", None, None, None, None),
                    PerfDataTuple("not_here", "not_here", 6, "M", 5.6, None, None, None),
                ],
                "test",
            ),
        ),
        (
            "11.26=6;;;;",
            "check_mk-local",
            (
                [
                    PerfDataTuple("11.26", "11.26", 6, "", None, None, None, None),
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
    assert parse_perf_data(perf_str, check_command, config=active_config) == result


def test_parse_perf_data2(request_context: None, set_config: SetConfig) -> None:
    with pytest.raises(ValueError), set_config(debug=True):
        parse_perf_data("hi ho", None, config=active_config)


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
        PerfDataTuple(metric_name, metric_name, 0, "", None, None, None, None),
        PerfDataTuple(predictive_metric_name, metric_name, 0, "", None, None, None, None),
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
    )
    assert translated_metrics[predictive_metric_name].title == expected_title
    assert (
        translated_metrics[predictive_metric_name].unit_spec
        == translated_metrics[metric_name].unit_spec
    )
    assert translated_metrics[predictive_metric_name].color == expected_color


def test_translate_metrics_with_multiple_predictive_metrics() -> None:
    perfdata: Perfdata = [
        PerfDataTuple("messages_outbound", "messages_outbound", 0, "", None, None, None, None),
        PerfDataTuple(
            "predict_messages_outbound", "messages_outbound", 0, "", None, None, None, None
        ),
        PerfDataTuple(
            "predict_lower_messages_outbound", "messages_outbound", 0, "", None, None, None, None
        ),
    ]
    translated_metrics = translate_metrics(perfdata, "my-check-plugin", {})
    assert translated_metrics["predict_messages_outbound"].color == "#4b4b4b"
    assert translated_metrics["predict_lower_messages_outbound"].color == "#5a5a5a"


@pytest.mark.parametrize(
    ["default_temperature_unit", "expected_value", "expected_scalars"],
    [
        pytest.param(
            TemperatureUnit.CELSIUS,
            59.05,
            {"warn": 85.05, "crit": 85.05},
            id="no unit conversion",
        ),
        pytest.param(
            TemperatureUnit.FAHRENHEIT,
            138.29,
            {"warn": 185.09, "crit": 185.09},
            id="with unit conversion",
        ),
    ],
)
def test_translate_metrics(
    default_temperature_unit: TemperatureUnit,
    expected_value: float,
    expected_scalars: Mapping[str, float],
    request_context: None,
) -> None:
    active_config.default_temperature_unit = default_temperature_unit.value
    translated_metric = translate_metrics(
        [PerfDataTuple("temp", "temp", 59.05, "", 85.05, 85.05, None, None)],
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
