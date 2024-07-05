#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.config import active_config
from cmk.gui.graphing._expression import (
    ConditionalMetricExpression,
    Constant,
    CriticalOf,
    Difference,
    GreaterEqualThan,
    GreaterThan,
    LessEqualThan,
    LessThan,
    MaximumOf,
    Metric,
    MetricExpression,
    MetricExpressionResult,
    MinimumOf,
    parse_conditional_expression,
    parse_expression,
    Percent,
    Product,
    Sum,
    WarningOf,
)
from cmk.gui.graphing._unit_info import unit_info
from cmk.gui.graphing._utils import graph_info, metric_info, parse_perf_data, translate_metrics
from cmk.gui.type_defs import Perfdata, PerfDataTuple


@pytest.mark.parametrize(
    "perf_data, expression, check_command, expected_result",
    [
        pytest.param(
            "util=605;;;0;100",
            "util,100,MAX",
            "check_mk-bintec_cpu",
            605.0,
        ),
        pytest.param(
            "user=4.600208;;;; system=1.570093;;;; io_wait=0.149533;;;;",
            "user,system,io_wait,+,+,100,MAX",
            "check_mk-kernel_util",
            100.0,
        ),
        pytest.param(
            "user=101.000000;;;; system=0.100000;;;; io_wait=0.010000;;;;",
            "user,system,io_wait,+,+,100,MAX",
            "check_mk-kernel_util",
            101.11,
        ),
    ],
)
def test_evaluate_cpu_utilization(
    perf_data: str, expression: str, check_command: str, expected_result: float
) -> None:
    """Clamping to upper value.

    Technically, the percent values for CPU Utilization should always be between 0 and 100. In
    practice, these values can be above 100. This was observed for docker (SUP-13161). In this
    case, it is sensible to extend the graph. This behaviour would be a sensible default, but
    currently using our `stack_resolver` is the only.

    This test provides a sanity check that the stack_resolver clamps the values in the way it
    should.
    """
    # Assemble
    assert metric_info, "Global variable is empty/has not been initialized."
    assert graph_info, "Global variable is empty/has not been initialized."
    perf_data_parsed, check_command = parse_perf_data(
        perf_data, check_command, config=active_config
    )
    translated_metrics = translate_metrics(perf_data_parsed, check_command)
    assert (
        parse_expression(expression, translated_metrics).evaluate(translated_metrics).value
        == expected_result
    )


@pytest.mark.parametrize(
    "perf_data, check_command, raw_expression, expected_metric_expression, value, unit_name, color",
    [
        pytest.param(
            [PerfDataTuple(n, n, len(n), "", 120, 240, 0, 24) for n in ["in", "out"]],
            "check_mk-openvpn_clients",
            "if_in_octets,8,*@bits/s",
            Product(
                factors=[Metric(name="if_in_octets"), Constant(value=8)],
                explicit_unit_name="bits/s",
            ),
            16.0,
            "bits/s",
            "#37fa37",
            id="already_migrated-warn, crit, min, max",
        ),
        # This is a terrible metric from Nagios plug-ins. Test is for survival instead of
        # correctness The unit "percent" is lost on the way. Fixing this would imply also
        # figuring out how to represent graphs for active-icmp check when host has multiple
        # addresses.
        pytest.param(
            parse_perf_data("127.0.0.1pl=5%;80;100;;", config=active_config)[0],
            "check_mk_active-icmp",
            "127.0.0.1pl",
            Metric(name="127.0.0.1pl"),
            5,
            "",
            "#cc00ff",
            id="warn crit None None",
        ),
        # Here the user has a metrics that represent subnets, but the values look like floats
        # Test that evaluation recognizes the metric from the perf data
        pytest.param(
            parse_perf_data("10.172=6", config=active_config)[0],
            "check_mk-local",
            "10.172",
            Metric(name="10.172"),
            6,
            "",
            "#cc00ff",
            id="None None None None",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            "97",
            Constant(value=97),
            97.0,
            "count",
            "#000000",
            id="constant str -> int",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            97,
            Constant(value=97),
            97.0,
            "count",
            "#000000",
            id="constant int",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            "97.0",
            Constant(value=97.0),
            97.0,
            "",
            "#000000",
            id="constant str -> float",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            97.0,
            Constant(value=97.0),
            97.0,
            "",
            "#000000",
            id="constant float",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            "97.0@bytes",
            Constant(value=97.0, explicit_unit_name="bytes"),
            97.0,
            "bytes",
            "#000000",
            id="constant unit",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            "97.0#123456",
            Constant(value=97.0, explicit_color="#123456"),
            97.0,
            "",
            "#123456",
            id="constant color",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name(%)",
            Percent(
                percent_value=Metric(name="metric_name"),
                base_value=MaximumOf(metric=Metric(name="metric_name")),
            ),
            20.0,
            "%",
            "#cc00ff",
            id="percentage",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:warn",
            WarningOf(metric=Metric(name="metric_name")),
            20.0,
            "",
            "#ffd000",
            id="warn",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:warn(%)",
            Percent(
                percent_value=WarningOf(metric=Metric(name="metric_name")),
                base_value=MaximumOf(metric=Metric(name="metric_name")),
            ),
            40.0,
            "%",
            "#ffd000",
            id="warn percentage",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:crit",
            CriticalOf(metric=Metric(name="metric_name")),
            30.0,
            "",
            "#ff3232",
            id="crit",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:crit(%)",
            Percent(
                percent_value=CriticalOf(metric=Metric(name="metric_name")),
                base_value=MaximumOf(metric=Metric(name="metric_name")),
            ),
            60.0,
            "%",
            "#ff3232",
            id="crit percentage",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:min",
            MinimumOf(metric=Metric(name="metric_name")),
            0.0,
            "",
            "#808080",
            id="min",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:min(%)",
            Percent(
                percent_value=MinimumOf(metric=Metric(name="metric_name")),
                base_value=MaximumOf(metric=Metric(name="metric_name")),
            ),
            0.0,
            "%",
            "#808080",
            id="min percentage",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:max",
            MaximumOf(metric=Metric(name="metric_name")),
            50.0,
            "",
            "#808080",
            id="max",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:max(%)",
            Percent(
                percent_value=MaximumOf(metric=Metric(name="metric_name")),
                base_value=MaximumOf(metric=Metric(name="metric_name")),
            ),
            100.0,
            "%",
            "#808080",
            id="max percentage",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name.max",
            Metric(name="metric_name", consolidation_func_name="max"),
            10.0,
            "",
            "#cc00ff",
            id="consolidation func name max",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name.min",
            Metric(name="metric_name", consolidation_func_name="min"),
            10.0,
            "",
            "#cc00ff",
            id="consolidation func name min",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name.average",
            Metric(name="metric_name", consolidation_func_name="average"),
            10.0,
            "",
            "#cc00ff",
            id="consolidation func name average",
        ),
    ],
)
def test_parse_and_evaluate_1(
    perf_data: Perfdata,
    check_command: str,
    raw_expression: str,
    expected_metric_expression: MetricExpression,
    value: float,
    unit_name: str,
    color: str,
) -> None:
    translated_metrics = translate_metrics(perf_data, check_command)
    metric_expression = parse_expression(raw_expression, translated_metrics)
    assert metric_expression == expected_metric_expression
    assert metric_expression.evaluate(translated_metrics) == MetricExpressionResult(
        value, unit_info[unit_name], color
    )


@pytest.mark.parametrize(
    "perf_data, check_command, raw_expression, expected_metric_expression, value, unit_name, color",
    [
        pytest.param(
            [PerfDataTuple(n, n, len(n), "", None, None, None, None) for n in ["/", "fs_size"]],
            "check_mk-df",
            "fs_size,fs_used,-#e3fff9",
            Difference(
                minuend=Metric(name="fs_size"),
                subtrahend=Metric(name="fs_used"),
                explicit_color="#e3fff9",
            ),
            6291456,
            "IECNotation_B_AutoPrecision_2",
            "#e3fff9",
            id="None None None None",
        ),
    ],
)
def test_parse_and_evaluate_2(
    perf_data: Perfdata,
    check_command: str,
    raw_expression: str,
    expected_metric_expression: MetricExpression,
    value: float,
    unit_name: str,
    color: str,
) -> None:
    translated_metrics = translate_metrics(perf_data, check_command)
    metric_expression = parse_expression(raw_expression, translated_metrics)
    assert metric_expression == expected_metric_expression
    result = metric_expression.evaluate(translated_metrics)
    assert result.value == value
    assert result.unit_info["id"] == unit_name
    assert result.color == color


@pytest.mark.parametrize(
    "perf_data, check_command, raw_expression, expected_conditional_metric_declaration, value",
    [
        pytest.param(
            [PerfDataTuple(n, n, 100, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name,100,>",
            GreaterThan(
                left=Metric(name="metric_name"),
                right=Constant(100),
            ),
            False,
            id="conditional greater than",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 100, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name,100,>=",
            GreaterEqualThan(
                left=Metric(name="metric_name"),
                right=Constant(100),
            ),
            True,
            id="conditional greater equal than",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 100, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name,100,<",
            LessThan(
                left=Metric(name="metric_name"),
                right=Constant(100),
            ),
            False,
            id="conditional less than",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 100, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name,100,<=",
            LessEqualThan(
                left=Metric(name="metric_name"),
                right=Constant(100),
            ),
            True,
            id="conditional less equal than",
        ),
        pytest.param(
            [
                PerfDataTuple("used", "used", 50, "", 20, 30, 0, 50),
                PerfDataTuple("uncommitted", "uncommitted", 50, "", 20, 30, 0, 50),
                PerfDataTuple("size", "size", 100, "", 20, 30, 0, 100),
            ],
            "check_mk-foo",
            "used,uncommitted,+,size,>",
            GreaterThan(
                left=Sum([Metric(name="used"), Metric(name="uncommitted")]),
                right=Metric(name="size"),
            ),
            False,
            id="conditional greater than nested",
        ),
        pytest.param(
            [
                PerfDataTuple(
                    "delivered_notifications", "delivered_notifications", 0, "", 0, 0, 0, 0
                ),
                PerfDataTuple("failed_notifications", "failed_notifications", 0, "", 0, 0, 0, 0),
            ],
            "check_mk-foo",
            "delivered_notifications,failed_notifications,+,delivered_notifications,failed_notifications,+,2,*,>=",
            GreaterEqualThan(
                left=Sum(
                    summands=[
                        Metric(name="delivered_notifications"),
                        Metric(name="failed_notifications"),
                    ]
                ),
                right=Product(
                    factors=[
                        Sum(
                            summands=[
                                Metric(name="delivered_notifications"),
                                Metric(name="failed_notifications"),
                            ]
                        ),
                        Constant(value=2),
                    ]
                ),
            ),
            True,
            id="conditional notifications greater than 1",
        ),
        pytest.param(
            [
                PerfDataTuple(
                    "delivered_notifications", "delivered_notifications", 1, "", 0, 0, 0, 0
                ),
                PerfDataTuple("failed_notifications", "failed_notifications", 0, "", 0, 0, 0, 0),
            ],
            "check_mk-foo",
            "delivered_notifications,failed_notifications,+,delivered_notifications,failed_notifications,+,2,*,>=",
            GreaterEqualThan(
                left=Sum(
                    summands=[
                        Metric(name="delivered_notifications"),
                        Metric(name="failed_notifications"),
                    ]
                ),
                right=Product(
                    factors=[
                        Sum(
                            summands=[
                                Metric(name="delivered_notifications"),
                                Metric(name="failed_notifications"),
                            ]
                        ),
                        Constant(value=2),
                    ]
                ),
            ),
            False,
            id="conditional notifications greater than 2",
        ),
        pytest.param(
            [
                PerfDataTuple(
                    "delivered_notifications", "delivered_notifications", 0, "", 0, 0, 0, 0
                ),
                PerfDataTuple("failed_notifications", "failed_notifications", 1, "", 0, 0, 0, 0),
            ],
            "check_mk-foo",
            "delivered_notifications,failed_notifications,+,delivered_notifications,failed_notifications,+,2,*,>=",
            GreaterEqualThan(
                left=Sum(
                    summands=[
                        Metric(name="delivered_notifications"),
                        Metric(name="failed_notifications"),
                    ]
                ),
                right=Product(
                    factors=[
                        Sum(
                            summands=[
                                Metric(name="delivered_notifications"),
                                Metric(name="failed_notifications"),
                            ]
                        ),
                        Constant(value=2),
                    ]
                ),
            ),
            False,
            id="conditional notifications greater than 3",
        ),
    ],
)
def test_parse_and_evaluate_conditional(
    perf_data: Perfdata,
    check_command: str,
    raw_expression: str,
    expected_conditional_metric_declaration: ConditionalMetricExpression,
    value: bool,
) -> None:
    translated_metrics = translate_metrics(perf_data, check_command)
    metric_declaration = parse_conditional_expression(raw_expression, translated_metrics)
    assert metric_declaration == expected_conditional_metric_declaration
    assert metric_declaration.evaluate(translated_metrics) == value
