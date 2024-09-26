#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.config import active_config
from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._legacy import unit_info, UnitInfo
from cmk.gui.graphing._metric_expression import (
    _FALLBACK_UNIT_SPEC_FLOAT,
    _FALLBACK_UNIT_SPEC_INT,
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
    MinimumOf,
    parse_legacy_conditional_expression,
    parse_legacy_expression,
    Percent,
    Product,
    Sum,
    WarningOf,
)
from cmk.gui.graphing._metric_operation import LineType
from cmk.gui.graphing._translated_metrics import parse_perf_data, translate_metrics
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation, IECNotation
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
    perf_data_parsed, check_command = parse_perf_data(
        perf_data, check_command, config=active_config
    )
    translated_metrics = translate_metrics(perf_data_parsed, check_command)
    result = parse_legacy_expression(expression, "line", "", translated_metrics).evaluate(
        translated_metrics
    )
    assert result.is_ok()
    assert result.ok.value == expected_result


@pytest.mark.parametrize(
    [
        "perf_data",
        "check_command",
        "raw_expression",
        "expected_metric_expression",
        "expected_value",
        "expected_unit_spec",
        "expected_color",
    ],
    [
        pytest.param(
            [PerfDataTuple(n, n, len(n), "", 120, 240, 0, 24) for n in ["in", "out"]],
            "check_mk-openvpn_clients",
            "if_in_octets,8,*@bits/s",
            MetricExpression(
                Product([Metric("if_in_octets"), Constant(8)]),
                line_type="line",
                unit_spec="bits/s",
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
            MetricExpression(Metric("127.0.0.1pl"), line_type="line"),
            5,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#cc00ff",
            id="warn crit None None",
        ),
        # Here the user has a metrics that represent subnets, but the values look like floats
        # Test that evaluation recognizes the metric from the perf data
        pytest.param(
            parse_perf_data("10.172=6", config=active_config)[0],
            "check_mk-local",
            "10.172",
            MetricExpression(Metric("10.172"), line_type="line"),
            6,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#cc00ff",
            id="None None None None",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            "97",
            MetricExpression(Constant(97), line_type="line"),
            97.0,
            _FALLBACK_UNIT_SPEC_INT,
            "#000000",
            id="constant str -> int",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            97,
            MetricExpression(Constant(97), line_type="line"),
            97.0,
            _FALLBACK_UNIT_SPEC_INT,
            "#000000",
            id="constant int",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            "97.0",
            MetricExpression(Constant(97.0), line_type="line"),
            97.0,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#000000",
            id="constant str -> float",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            97.0,
            MetricExpression(Constant(97.0), line_type="line"),
            97.0,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#000000",
            id="constant float",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            "97.0@bytes",
            MetricExpression(Constant(97.0), line_type="line", unit_spec="bytes"),
            97.0,
            "bytes",
            "#000000",
            id="constant unit",
        ),
        pytest.param(
            [],
            "check_mk-foo",
            "97.0#123456",
            MetricExpression(Constant(97.0), line_type="line", color="#123456"),
            97.0,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#123456",
            id="constant color",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name(%)",
            MetricExpression(
                Percent(
                    percent_value=Metric("metric_name"),
                    base_value=MaximumOf(Metric("metric_name")),
                ),
                line_type="line",
            ),
            20.0,
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="%"),
                precision=AutoPrecision(digits=2),
            ),
            "#cc00ff",
            id="percentage",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:warn",
            MetricExpression(WarningOf(Metric("metric_name")), line_type="line"),
            20.0,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#ffd000",
            id="warn",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:warn(%)",
            MetricExpression(
                Percent(
                    percent_value=WarningOf(Metric("metric_name")),
                    base_value=MaximumOf(Metric("metric_name")),
                ),
                line_type="line",
            ),
            40.0,
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="%"),
                precision=AutoPrecision(digits=2),
            ),
            "#ffd000",
            id="warn percentage",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:crit",
            MetricExpression(CriticalOf(Metric("metric_name")), line_type="line"),
            30.0,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#ff3232",
            id="crit",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:crit(%)",
            MetricExpression(
                Percent(
                    percent_value=CriticalOf(Metric("metric_name")),
                    base_value=MaximumOf(Metric("metric_name")),
                ),
                line_type="line",
            ),
            60.0,
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="%"),
                precision=AutoPrecision(digits=2),
            ),
            "#ff3232",
            id="crit percentage",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:min",
            MetricExpression(MinimumOf(Metric("metric_name")), line_type="line"),
            0.0,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#808080",
            id="min",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:min(%)",
            MetricExpression(
                Percent(
                    percent_value=MinimumOf(Metric("metric_name")),
                    base_value=MaximumOf(Metric("metric_name")),
                ),
                line_type="line",
            ),
            0.0,
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="%"),
                precision=AutoPrecision(digits=2),
            ),
            "#808080",
            id="min percentage",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:max",
            MetricExpression(MaximumOf(Metric("metric_name")), line_type="line"),
            50.0,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#808080",
            id="max",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name:max(%)",
            MetricExpression(
                Percent(
                    percent_value=MaximumOf(Metric("metric_name")),
                    base_value=MaximumOf(Metric("metric_name")),
                ),
                line_type="line",
            ),
            100.0,
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="%"),
                precision=AutoPrecision(digits=2),
            ),
            "#808080",
            id="max percentage",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name.max",
            MetricExpression(Metric("metric_name", "max"), line_type="line"),
            10.0,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#cc00ff",
            id="consolidation func name max",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name.min",
            MetricExpression(Metric("metric_name", "min"), line_type="line"),
            10.0,
            _FALLBACK_UNIT_SPEC_FLOAT,
            "#cc00ff",
            id="consolidation func name min",
        ),
        pytest.param(
            [PerfDataTuple(n, n, 10, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name.average",
            MetricExpression(Metric("metric_name", "average"), line_type="line"),
            10.0,
            _FALLBACK_UNIT_SPEC_FLOAT,
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
    expected_value: float,
    expected_unit_spec: str | ConvertibleUnitSpecification,
    expected_color: str,
) -> None:
    translated_metrics = translate_metrics(perf_data, check_command)
    metric_expression = parse_legacy_expression(raw_expression, "line", "", translated_metrics)
    assert metric_expression == expected_metric_expression

    result = metric_expression.evaluate(translated_metrics)
    assert result.is_ok()
    assert result.ok.value == expected_value
    assert result.ok.color == expected_color

    if isinstance(expected_unit_spec, ConvertibleUnitSpecification):
        assert result.ok.unit_spec == expected_unit_spec
    else:
        assert isinstance(result.ok.unit_spec, UnitInfo)
        unit_info_ = unit_info[expected_unit_spec]
        assert result.ok.unit_spec.id == unit_info_.id
        assert result.ok.unit_spec.title == unit_info_.title
        assert result.ok.unit_spec.symbol == unit_info_.symbol
        assert result.ok.unit_spec.render == unit_info_.render
        assert result.ok.unit_spec.js_render == unit_info_.js_render
        assert result.ok.unit_spec.stepping == unit_info_.stepping
        assert result.ok.unit_spec.color == unit_info_.color
        assert result.ok.unit_spec.graph_unit == unit_info_.graph_unit
        assert result.ok.unit_spec.description == unit_info_.description
        assert result.ok.unit_spec.valuespec == unit_info_.valuespec
        assert result.ok.unit_spec.perfometer_render == unit_info_.perfometer_render
        assert result.ok.unit_spec.conversion(123.456) == 123.456


@pytest.mark.parametrize(
    [
        "perf_data",
        "check_command",
        "raw_expression",
        "expected_metric_expression",
        "expected_value",
        "expected_unit_spec",
        "expected_color",
    ],
    [
        pytest.param(
            [PerfDataTuple(n, n, len(n), "", None, None, None, None) for n in ["/", "fs_size"]],
            "check_mk-df",
            "fs_size,fs_used,-#e3fff9",
            MetricExpression(
                Difference(minuend=Metric("fs_size"), subtrahend=Metric("fs_used")),
                line_type="line",
                color="#e3fff9",
            ),
            6291456,
            ConvertibleUnitSpecification(
                notation=IECNotation(symbol="B"),
                precision=AutoPrecision(digits=2),
            ),
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
    expected_value: float,
    expected_unit_spec: ConvertibleUnitSpecification,
    expected_color: str,
) -> None:
    translated_metrics = translate_metrics(perf_data, check_command)
    metric_expression = parse_legacy_expression(raw_expression, "line", "", translated_metrics)
    assert metric_expression == expected_metric_expression

    result = metric_expression.evaluate(translated_metrics)
    assert result.is_ok()
    assert result.ok.value == expected_value
    assert result.ok.unit_spec == expected_unit_spec
    assert result.ok.color == expected_color


@pytest.mark.parametrize(
    "perf_data, check_command, raw_expression, expected_conditional_metric_declaration, value",
    [
        pytest.param(
            [PerfDataTuple(n, n, 100, "", 20, 30, 0, 50) for n in ["metric_name"]],
            "check_mk-foo",
            "metric_name,100,>",
            GreaterThan(
                left=Metric("metric_name"),
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
                left=Metric("metric_name"),
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
                left=Metric("metric_name"),
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
                left=Metric("metric_name"),
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
                left=Sum([Metric("used"), Metric("uncommitted")]),
                right=Metric("size"),
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
                    [
                        Metric("delivered_notifications"),
                        Metric("failed_notifications"),
                    ]
                ),
                right=Product(
                    [
                        Sum(
                            [
                                Metric("delivered_notifications"),
                                Metric("failed_notifications"),
                            ]
                        ),
                        Constant(2),
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
                    [
                        Metric("delivered_notifications"),
                        Metric("failed_notifications"),
                    ]
                ),
                right=Product(
                    [
                        Sum(
                            [
                                Metric("delivered_notifications"),
                                Metric("failed_notifications"),
                            ]
                        ),
                        Constant(2),
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
                    [
                        Metric("delivered_notifications"),
                        Metric("failed_notifications"),
                    ]
                ),
                right=Product(
                    [
                        Sum(
                            [
                                Metric("delivered_notifications"),
                                Metric("failed_notifications"),
                            ]
                        ),
                        Constant(2),
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
    metric_declaration = parse_legacy_conditional_expression(raw_expression, translated_metrics)
    assert metric_declaration == expected_conditional_metric_declaration
    assert metric_declaration.evaluate(translated_metrics) == value


@pytest.mark.parametrize(
    "line_type, expected_line_type",
    [
        pytest.param("line", "-line", id="'line'->'-line'"),
        pytest.param("-line", "line", id="'-line'->'line'"),
        pytest.param("area", "-area", id="'area'->'-area'"),
        pytest.param("-area", "area", id="'-area'->'area'"),
        pytest.param("stack", "-stack", id="'stack'->'-stack'"),
        pytest.param("-stack", "stack", id="'-stack'->'stack'"),
    ],
)
def test_metric_expression_mirror(line_type: LineType, expected_line_type: LineType) -> None:
    assert MetricExpression(
        Metric("metric-name"),
        unit_spec="unit",
        color="#000000",
        line_type=line_type,
        title="Title",
    ).mirror() == MetricExpression(
        Metric("metric-name"),
        unit_spec="unit",
        color="#000000",
        line_type=expected_line_type,
        title="Title",
    )
