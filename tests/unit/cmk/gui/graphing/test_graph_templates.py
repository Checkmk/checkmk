#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import pytest
from pytest import MonkeyPatch

from livestatus import SiteId

from cmk.utils.hostaddress import HostName

from cmk.gui.config import active_config
from cmk.gui.graphing import _graph_templates as gt
from cmk.gui.graphing._expression import (
    Constant,
    CriticalOf,
    Difference,
    Fraction,
    Maximum,
    MaximumOf,
    Metric,
    Minimum,
    MinimumOf,
    Product,
    Sum,
    WarningOf,
)
from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._from_api import metrics_from_api, RegisteredMetric
from cmk.gui.graphing._graph_specification import (
    HorizontalRule,
    MetricOpOperator,
    MetricOpRRDSource,
)
from cmk.gui.graphing._graph_templates import (
    _compute_predictive_metrics,
    _graph_template_from_api_bidirectional,
    _graph_template_from_api_graph,
    _graph_template_from_legacy,
    _graph_templates_from_plugins,
    _matching_graph_templates,
    _parse_graph_template,
    get_graph_templates,
    GraphTemplate,
    MetricDefinition,
    MinimalGraphTemplateRange,
    ScalarDefinition,
)
from cmk.gui.graphing._legacy import RawGraphTemplate, UnitInfo
from cmk.gui.graphing._translated_metrics import (
    Original,
    parse_perf_data,
    translate_metrics,
    TranslatedMetric,
)
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.type_defs import Perfdata, PerfDataTuple

from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import Title

_GRAPH_TEMPLATES = [
    GraphTemplate(
        id="1",
        title="Graph 1",
        scalars=[],
        conflicting_metrics=[],
        optional_metrics=[],
        consolidation_function=None,
        range=None,
        omit_zero_metrics=False,
        metrics=[],
    ),
    GraphTemplate(
        id="2",
        title="Graph 2",
        scalars=[],
        conflicting_metrics=[],
        optional_metrics=[],
        consolidation_function=None,
        range=None,
        omit_zero_metrics=False,
        metrics=[],
    ),
]


@pytest.mark.parametrize(
    ("graph_id", "graph_index", "expected_result"),
    [
        pytest.param(
            None,
            None,
            list(enumerate(_GRAPH_TEMPLATES)),
            id="no index and no id",
        ),
        pytest.param(
            None,
            0,
            [(0, _GRAPH_TEMPLATES[0])],
            id="matching index and no id",
        ),
        pytest.param(
            None,
            10,
            [],
            id="non-matching index and no id",
        ),
        pytest.param(
            "2",
            None,
            [(1, _GRAPH_TEMPLATES[1])],
            id="no index and matching id",
        ),
        pytest.param(
            "wrong",
            None,
            [],
            id="no index and non-matching id",
        ),
        pytest.param(
            "1",
            0,
            [(0, _GRAPH_TEMPLATES[0])],
            id="matching index and matching id",
        ),
        pytest.param(
            "2",
            0,
            [],
            id="inconsistent matching index and matching id",
        ),
    ],
)
def test__matching_graph_templates(
    monkeypatch: MonkeyPatch,
    graph_id: str | None,
    graph_index: int | None,
    expected_result: Sequence[tuple[int, GraphTemplate]],
) -> None:
    monkeypatch.setattr(
        gt,
        "get_graph_templates",
        lambda _metrics: _GRAPH_TEMPLATES,
    )
    assert (
        list(
            _matching_graph_templates(
                graph_id=graph_id,
                graph_index=graph_index,
                translated_metrics={},
            )
        )
        == expected_result
    )


def test__replace_expressions() -> None:
    perfdata: Perfdata = [PerfDataTuple(n, n, len(n), "", 120, 240, 0, 25) for n in ["load1"]]
    translated_metrics = translate_metrics(perfdata, "check_mk-cpu.loads")
    assert (
        gt._replace_expressions("CPU Load - %(load1:max@count) CPU Cores", translated_metrics)
        == "CPU Load - 25 CPU Cores"
    )


def test__replace_expressions_missing_scalars() -> None:
    perfdata: Perfdata = [
        PerfDataTuple(n, n, len(n), "", None, None, None, None) for n in ["load1"]
    ]
    translated_metrics = translate_metrics(perfdata, "check_mk-cpu.loads")
    assert (
        gt._replace_expressions("CPU Load - %(load1:max@count) CPU Cores", translated_metrics)
        == "CPU Load"
    )


@pytest.mark.parametrize(
    "perf_data_string, result",
    [
        pytest.param(
            "one=5;;;; power=5;;;; output=5;;;;",
            [],
            id="Unknown thresholds from check",
        ),
        pytest.param(
            "one=5;7;6;; power=5;9;10;; output=5;2;3;;",
            [
                HorizontalRule(
                    value=7.0,
                    rendered_value="7.00",
                    color="#ffd000",
                    title="Warning",
                ),
                HorizontalRule(
                    value=10.0,
                    rendered_value="10 W",
                    color="#ff3232",
                    title="Critical power",
                ),
                HorizontalRule(
                    value=-2.0,
                    rendered_value="-2.00",
                    color="#ffd000",
                    title="Warning output",
                ),
            ],
            id="Thresholds present",
        ),
    ],
)
def test_horizontal_rules_from_thresholds(
    perf_data_string: str, result: Sequence[HorizontalRule]
) -> None:
    perf_data, check_command = parse_perf_data(perf_data_string, None, config=active_config)
    translated_metrics = translate_metrics(perf_data, check_command)
    assert (
        gt._horizontal_rules_from_thresholds(
            [
                ScalarDefinition(
                    expression=WarningOf(Metric("one")),
                    title="Warning",
                ),
                ScalarDefinition(
                    expression=CriticalOf(Metric("power")),
                    title="Critical power",
                ),
                ScalarDefinition(
                    expression=Product([WarningOf(Metric("output")), Constant(-1)]),
                    title="Warning output",
                ),
            ],
            translated_metrics,
        )
        == result
    )


def test_duplicate_graph_templates(request_context: None) -> None:
    idents_by_metrics: dict[tuple[str, ...], list[str]] = {}
    for id_, template in _graph_templates_from_plugins():
        parsed = _parse_graph_template(id_, template)
        expressions = [m.expression for m in parsed.metrics] + [
            s.expression for s in parsed.scalars
        ]
        if parsed.range:
            expressions.extend((parsed.range.min, parsed.range.max))

        idents_by_metrics.setdefault(
            tuple(sorted(n for e in expressions for n in e.metric_names())), []
        ).append(parsed.id)

    assert {tuple(idents) for idents in idents_by_metrics.values() if len(idents) >= 2} == {
        ("livestatus_requests_per_connection", "livestatus_connects_and_requests"),
    }


def test_graph_template_with_layered_areas(request_context: None) -> None:
    # area, area, ... -> two layers
    # area, stack, ... -> one layer
    # stack, stack, ... -> one layer
    @dataclass
    class _GraphTemplateArea:
        pos: list[Literal["area", "stack"]] = field(default_factory=list)
        neg: list[Literal["-area", "-stack"]] = field(default_factory=list)

    areas_by_ident: dict[str, _GraphTemplateArea] = {}
    for id_, template in _graph_templates_from_plugins():
        parsed = _parse_graph_template(id_, template)
        for metric in parsed.metrics:
            if metric.line_type == "area":
                areas_by_ident.setdefault(parsed.id, _GraphTemplateArea()).pos.append(
                    metric.line_type
                )
            elif metric.line_type == "stack":
                areas_by_ident.setdefault(parsed.id, _GraphTemplateArea()).pos.append(
                    metric.line_type
                )
            elif metric.line_type == "-area":
                areas_by_ident.setdefault(parsed.id, _GraphTemplateArea()).neg.append(
                    metric.line_type
                )
            elif metric.line_type == "-stack":
                areas_by_ident.setdefault(parsed.id, _GraphTemplateArea()).neg.append(
                    metric.line_type
                )

    templates_with_more_than_one_layer = [
        ident
        for ident, areas in areas_by_ident.items()
        if areas.pos.count("area") > 1 or areas.neg.count("-area") > 1
    ]
    assert not templates_with_more_than_one_layer


@pytest.mark.parametrize(
    "orig_names, scales, expected_operation",
    [
        pytest.param(
            ["metric-name"],
            [1.0],
            MetricOpRRDSource(
                site_id=SiteId("Site-ID"),
                host_name=HostName("HostName"),
                service_name="Service description",
                metric_name="metric-name",
                consolidation_func_name=None,
                scale=1.0,
            ),
            id="no translation",
        ),
        pytest.param(
            ["metric-name", "old-metric-name"],
            [1.0, 2.0],
            MetricOpOperator(
                operator_name="MERGE",
                operands=[
                    MetricOpRRDSource(
                        site_id=SiteId("Site-ID"),
                        host_name=HostName("HostName"),
                        service_name="Service description",
                        metric_name="metric-name",
                        consolidation_func_name=None,
                        scale=1.0,
                    ),
                    MetricOpRRDSource(
                        site_id=SiteId("Site-ID"),
                        host_name=HostName("HostName"),
                        service_name="Service description",
                        metric_name="old-metric-name",
                        consolidation_func_name=None,
                        scale=2.0,
                    ),
                ],
            ),
            id="translation",
        ),
    ],
)
def test__to_metric_operation(
    orig_names: Sequence[str],
    scales: Sequence[int | float],
    expected_operation: MetricOpOperator | MetricOpRRDSource,
) -> None:
    assert (
        gt._to_metric_operation(
            SiteId("Site-ID"),
            HostName("HostName"),
            "Service description",
            Metric("metric-name"),
            {
                "metric-name": TranslatedMetric(
                    originals=[Original(n, s) for n, s in zip(orig_names, scales)],
                    value=23.5,
                    scalar={},
                    auto_graph=False,
                    title="Title",
                    unit_info=UnitInfo(
                        id="id",
                        title="Title",
                        symbol="",
                        render=lambda v: f"{v}",
                        js_render="v => v",
                        conversion=lambda v: v,
                    ),
                    color="#111111",
                ),
            },
            None,
        )
        == expected_operation
    )


UNIT = metrics_api.Unit(metrics_api.DecimalNotation(""))
COLOR = metrics_api.Color.BLUE
COLOR_HEX = "#1e90ff"


@pytest.mark.parametrize(
    "graph, raw_metric_names, expected_template",
    [
        pytest.param(
            graphs_api.Graph(
                name="name",
                title=Title("Title"),
                compound_lines=[
                    "metric-name-1",
                    metrics_api.Constant(Title("Constant"), UNIT, COLOR, 10),
                    metrics_api.WarningOf("metric-name-2"),
                    metrics_api.CriticalOf("metric-name-3"),
                    metrics_api.MinimumOf("metric-name-4", COLOR),
                    metrics_api.MaximumOf("metric-name-5", COLOR),
                    metrics_api.Sum(
                        Title("Sum"),
                        COLOR,
                        ["metric-name-6"],
                    ),
                    metrics_api.Product(
                        Title("Product"),
                        UNIT,
                        COLOR,
                        ["metric-name-7"],
                    ),
                    metrics_api.Difference(
                        Title("Difference"),
                        COLOR,
                        minuend="metric-name-7",
                        subtrahend="metric-name-8",
                    ),
                    metrics_api.Fraction(
                        Title("Fraction"),
                        UNIT,
                        COLOR,
                        dividend="metric-name-9",
                        divisor="metric-name-10",
                    ),
                ],
            ),
            [
                "metric-name-1",
                "metric-name-2",
                "metric-name-3",
                "metric-name-4",
                "metric-name-5",
                "metric-name-6",
                "metric-name-7",
                "metric-name-8",
                "metric-name-9",
                "metric-name-10",
            ],
            GraphTemplate(
                id="name",
                title="Title",
                scalars=[],
                conflicting_metrics=(),
                optional_metrics=(),
                consolidation_function=None,
                range=None,
                omit_zero_metrics=False,
                metrics=[
                    MetricDefinition(
                        Metric("metric-name-1"),
                        "stack",
                        "Title",
                    ),
                    MetricDefinition(
                        Constant(
                            value=10,
                            unit_id="DecimalNotation__AutoPrecision_2",
                            color=COLOR_HEX,
                        ),
                        "stack",
                        "Constant",
                    ),
                    MetricDefinition(
                        WarningOf(Metric("metric-name-2")),
                        "stack",
                        "Warning of Title",
                    ),
                    MetricDefinition(
                        CriticalOf(Metric("metric-name-3")),
                        "stack",
                        "Critical of Title",
                    ),
                    MetricDefinition(
                        MinimumOf(
                            Metric("metric-name-4"),
                            color=COLOR_HEX,
                        ),
                        "stack",
                        "Title",
                    ),
                    MetricDefinition(
                        MaximumOf(
                            Metric("metric-name-5"),
                            color=COLOR_HEX,
                        ),
                        "stack",
                        "Title",
                    ),
                    MetricDefinition(
                        Sum(
                            [Metric("metric-name-6")],
                            color=COLOR_HEX,
                        ),
                        "stack",
                        "Sum",
                    ),
                    MetricDefinition(
                        Product(
                            [Metric("metric-name-7")],
                            unit_id="DecimalNotation__AutoPrecision_2",
                            color=COLOR_HEX,
                        ),
                        "stack",
                        "Product",
                    ),
                    MetricDefinition(
                        Difference(
                            minuend=Metric("metric-name-7"),
                            subtrahend=Metric("metric-name-8"),
                            color=COLOR_HEX,
                        ),
                        "stack",
                        "Difference",
                    ),
                    MetricDefinition(
                        Fraction(
                            dividend=Metric("metric-name-9"),
                            divisor=Metric("metric-name-10"),
                            unit_id="DecimalNotation__AutoPrecision_2",
                            color=COLOR_HEX,
                        ),
                        "stack",
                        "Fraction",
                    ),
                ],
            ),
            id="compound-lines",
        ),
        pytest.param(
            graphs_api.Graph(
                name="name",
                title=Title("Title"),
                simple_lines=[
                    "metric-name-1",
                    metrics_api.Constant(Title("Constant"), UNIT, COLOR, 10),
                    metrics_api.WarningOf("metric-name-2"),
                    metrics_api.CriticalOf("metric-name-3"),
                    metrics_api.MinimumOf("metric-name-4", COLOR),
                    metrics_api.MaximumOf("metric-name-5", COLOR),
                    metrics_api.Sum(
                        Title("Sum"),
                        COLOR,
                        ["metric-name-6"],
                    ),
                    metrics_api.Product(
                        Title("Product"),
                        UNIT,
                        COLOR,
                        ["metric-name-7"],
                    ),
                    metrics_api.Difference(
                        Title("Difference"),
                        COLOR,
                        minuend="metric-name-7",
                        subtrahend="metric-name-8",
                    ),
                    metrics_api.Fraction(
                        Title("Fraction"),
                        UNIT,
                        COLOR,
                        dividend="metric-name-9",
                        divisor="metric-name-10",
                    ),
                ],
            ),
            [
                "metric-name-1",
                "metric-name-2",
                "metric-name-3",
                "metric-name-4",
                "metric-name-5",
                "metric-name-6",
                "metric-name-7",
                "metric-name-8",
                "metric-name-9",
                "metric-name-10",
            ],
            GraphTemplate(
                id="name",
                title="Title",
                scalars=[
                    ScalarDefinition(
                        WarningOf(Metric("metric-name-2")),
                        "Warning of Title",
                    ),
                    ScalarDefinition(
                        CriticalOf(Metric("metric-name-3")),
                        "Critical of Title",
                    ),
                    ScalarDefinition(
                        MinimumOf(
                            Metric("metric-name-4"),
                            color=COLOR_HEX,
                        ),
                        "Title",
                    ),
                    ScalarDefinition(
                        MaximumOf(
                            Metric("metric-name-5"),
                            color=COLOR_HEX,
                        ),
                        "Title",
                    ),
                ],
                conflicting_metrics=(),
                optional_metrics=(),
                consolidation_function=None,
                range=None,
                omit_zero_metrics=False,
                metrics=[
                    MetricDefinition(
                        Metric("metric-name-1"),
                        "line",
                        "Title",
                    ),
                    MetricDefinition(
                        Constant(
                            value=10,
                            unit_id="DecimalNotation__AutoPrecision_2",
                            color=COLOR_HEX,
                        ),
                        "line",
                        "Constant",
                    ),
                    MetricDefinition(
                        Sum(
                            [Metric("metric-name-6")],
                            color=COLOR_HEX,
                        ),
                        "line",
                        "Sum",
                    ),
                    MetricDefinition(
                        Product(
                            [Metric("metric-name-7")],
                            unit_id="DecimalNotation__AutoPrecision_2",
                            color=COLOR_HEX,
                        ),
                        "line",
                        "Product",
                    ),
                    MetricDefinition(
                        Difference(
                            minuend=Metric("metric-name-7"),
                            subtrahend=Metric("metric-name-8"),
                            color=COLOR_HEX,
                        ),
                        "line",
                        "Difference",
                    ),
                    MetricDefinition(
                        Fraction(
                            dividend=Metric("metric-name-9"),
                            divisor=Metric("metric-name-10"),
                            unit_id="DecimalNotation__AutoPrecision_2",
                            color=COLOR_HEX,
                        ),
                        "line",
                        "Fraction",
                    ),
                ],
            ),
            id="simple-lines",
        ),
        pytest.param(
            graphs_api.Graph(
                name="name",
                title=Title("Title"),
                minimal_range=graphs_api.MinimalRange(0, 100.0),
                simple_lines=["metric-name"],
            ),
            ["metric-name"],
            GraphTemplate(
                id="name",
                title="Title",
                range=MinimalGraphTemplateRange(min=Constant(0), max=Constant(100.0)),
                scalars=[],
                conflicting_metrics=(),
                optional_metrics=(),
                consolidation_function=None,
                omit_zero_metrics=False,
                metrics=[MetricDefinition(Metric("metric-name"), "line", "Title")],
            ),
            id="explicit-range",
        ),
        pytest.param(
            graphs_api.Graph(
                name="name",
                title=Title("Title"),
                simple_lines=["metric-name"],
                optional=["metric-name-opt"],
                conflicting=["metric-name-confl"],
            ),
            ["metric-name"],
            GraphTemplate(
                id="name",
                title="Title",
                range=None,
                scalars=[],
                conflicting_metrics=["metric-name-confl"],
                optional_metrics=["metric-name-opt"],
                consolidation_function=None,
                omit_zero_metrics=False,
                metrics=[MetricDefinition(Metric("metric-name"), "line", "Title")],
            ),
            id="optional-conflicting",
        ),
    ],
)
def test__graph_template_from_api_graph(
    graph: graphs_api.Graph, raw_metric_names: Sequence[str], expected_template: GraphTemplate
) -> None:
    for r in raw_metric_names:
        metrics_from_api.register(
            RegisteredMetric(
                name=r,
                title_localizer=lambda _: "Title",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                api_unit=metrics_api.Unit(metrics_api.DecimalNotation("")),
                color="#000000",
            )
        )
    assert _graph_template_from_api_graph(graph.name, graph) == expected_template


@pytest.mark.parametrize(
    "graph, raw_metric_names, expected_template",
    [
        pytest.param(
            graphs_api.Bidirectional(
                name="name",
                title=Title("Title"),
                lower=graphs_api.Graph(
                    name="name-lower",
                    title=Title("Title lower"),
                    compound_lines=["metric-name-l1"],
                    simple_lines=[
                        "metric-name-l2",
                        metrics_api.WarningOf("metric-name-l3"),
                        metrics_api.CriticalOf("metric-name-l4"),
                        metrics_api.MinimumOf("metric-name-l5", COLOR),
                        metrics_api.MaximumOf("metric-name-l6", COLOR),
                    ],
                    optional=["metric-name-opt-l"],
                    conflicting=["metric-name-confl-l"],
                ),
                upper=graphs_api.Graph(
                    name="name-upper",
                    title=Title("Title upper"),
                    compound_lines=["metric-name-u1"],
                    simple_lines=[
                        "metric-name-u2",
                        metrics_api.WarningOf("metric-name-u3"),
                        metrics_api.CriticalOf("metric-name-u4"),
                        metrics_api.MinimumOf("metric-name-u5", COLOR),
                        metrics_api.MaximumOf("metric-name-u6", COLOR),
                    ],
                    optional=["metric-name-opt-u"],
                    conflicting=["metric-name-confl-u"],
                ),
            ),
            [
                "metric-name-l1",
                "metric-name-l2",
                "metric-name-l3",
                "metric-name-l4",
                "metric-name-l5",
                "metric-name-l6",
                "metric-name-u1",
                "metric-name-u2",
                "metric-name-u3",
                "metric-name-u4",
                "metric-name-u5",
                "metric-name-u6",
            ],
            GraphTemplate(
                id="name",
                title="Title",
                range=None,
                scalars=[
                    ScalarDefinition(
                        WarningOf(Metric("metric-name-l3")),
                        "Warning of Title",
                    ),
                    ScalarDefinition(
                        CriticalOf(Metric("metric-name-l4")),
                        "Critical of Title",
                    ),
                    ScalarDefinition(
                        MinimumOf(Metric("metric-name-l5"), color=COLOR_HEX),
                        "Title",
                    ),
                    ScalarDefinition(
                        MaximumOf(Metric("metric-name-l6"), color=COLOR_HEX),
                        "Title",
                    ),
                    ScalarDefinition(
                        WarningOf(Metric("metric-name-u3")),
                        "Warning of Title",
                    ),
                    ScalarDefinition(
                        CriticalOf(Metric("metric-name-u4")),
                        "Critical of Title",
                    ),
                    ScalarDefinition(
                        MinimumOf(Metric("metric-name-u5"), color=COLOR_HEX),
                        "Title",
                    ),
                    ScalarDefinition(
                        MaximumOf(Metric("metric-name-u6"), color=COLOR_HEX),
                        "Title",
                    ),
                ],
                conflicting_metrics=["metric-name-confl-l", "metric-name-confl-u"],
                optional_metrics=["metric-name-opt-l", "metric-name-opt-u"],
                consolidation_function=None,
                omit_zero_metrics=False,
                metrics=[
                    MetricDefinition(Metric("metric-name-l1"), "-stack", "Title"),
                    MetricDefinition(Metric("metric-name-u1"), "stack", "Title"),
                    MetricDefinition(Metric("metric-name-l2"), "-line", "Title"),
                    MetricDefinition(Metric("metric-name-u2"), "line", "Title"),
                ],
            ),
            id="lower-upper",
        ),
        pytest.param(
            graphs_api.Bidirectional(
                name="name",
                title=Title("Title"),
                lower=graphs_api.Graph(
                    name="name-lower",
                    title=Title("Title lower"),
                    minimal_range=graphs_api.MinimalRange(1, 10),
                    simple_lines=["metric-name-l"],
                ),
                upper=graphs_api.Graph(
                    name="name-upper",
                    title=Title("Title upper"),
                    minimal_range=graphs_api.MinimalRange(2, 11),
                    simple_lines=["metric-name-u"],
                ),
            ),
            ["metric-name-l", "metric-name-u"],
            GraphTemplate(
                id="name",
                title="Title",
                range=MinimalGraphTemplateRange(
                    min=Minimum([Constant(1), Constant(2)]),
                    max=Maximum([Constant(10), Constant(11)]),
                ),
                scalars=[],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                omit_zero_metrics=False,
                metrics=[
                    MetricDefinition(Metric("metric-name-l"), "-line", "Title"),
                    MetricDefinition(Metric("metric-name-u"), "line", "Title"),
                ],
            ),
            id="range-both",
        ),
        pytest.param(
            graphs_api.Bidirectional(
                name="name",
                title=Title("Title"),
                lower=graphs_api.Graph(
                    name="name-lower",
                    title=Title("Title lower"),
                    minimal_range=graphs_api.MinimalRange(1, 10),
                    simple_lines=["metric-name-l"],
                ),
                upper=graphs_api.Graph(
                    name="name-upper",
                    title=Title("Title upper"),
                    simple_lines=["metric-name-u"],
                ),
            ),
            ["metric-name-l", "metric-name-u"],
            GraphTemplate(
                id="name",
                title="Title",
                range=MinimalGraphTemplateRange(
                    min=Minimum([Constant(1)]),
                    max=Maximum([Constant(10)]),
                ),
                scalars=[],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                omit_zero_metrics=False,
                metrics=[
                    MetricDefinition(Metric("metric-name-l"), "-line", "Title"),
                    MetricDefinition(Metric("metric-name-u"), "line", "Title"),
                ],
            ),
            id="range-only-lower",
        ),
        pytest.param(
            graphs_api.Bidirectional(
                name="name",
                title=Title("Title"),
                lower=graphs_api.Graph(
                    name="name-lower",
                    title=Title("Title lower"),
                    simple_lines=["metric-name-l"],
                ),
                upper=graphs_api.Graph(
                    name="name-upper",
                    title=Title("Title upper"),
                    minimal_range=graphs_api.MinimalRange(2, 11),
                    simple_lines=["metric-name-u"],
                ),
            ),
            ["metric-name-l", "metric-name-u"],
            GraphTemplate(
                id="name",
                title="Title",
                range=MinimalGraphTemplateRange(
                    min=Minimum([Constant(2)]),
                    max=Maximum([Constant(11)]),
                ),
                scalars=[],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                omit_zero_metrics=False,
                metrics=[
                    MetricDefinition(Metric("metric-name-l"), "-line", "Title"),
                    MetricDefinition(Metric("metric-name-u"), "line", "Title"),
                ],
            ),
            id="range-only-upper",
        ),
    ],
)
def test__graph_template_from_api_bidirectional(
    graph: graphs_api.Bidirectional,
    raw_metric_names: Sequence[str],
    expected_template: GraphTemplate,
) -> None:
    for r in raw_metric_names:
        metrics_from_api.register(
            RegisteredMetric(
                name=r,
                title_localizer=lambda _: "Title",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                api_unit=metrics_api.Unit(metrics_api.DecimalNotation("")),
                color="#000000",
            )
        )
    assert _graph_template_from_api_bidirectional(graph.name, graph) == expected_template


@pytest.mark.parametrize(
    "raw, expected_graph_template",
    [
        pytest.param(
            RawGraphTemplate(
                metrics=[],
                scalars=["metric", "metric:warn", "metric:crit"],
            ),
            GraphTemplate(
                id="ident",
                title="",
                scalars=[
                    ScalarDefinition(
                        expression=Metric("metric"),
                        title="metric",
                    ),
                    ScalarDefinition(
                        expression=WarningOf(Metric("metric")),
                        title="Warning",
                    ),
                    ScalarDefinition(
                        expression=CriticalOf(Metric("metric")),
                        title="Critical",
                    ),
                ],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                range=None,
                omit_zero_metrics=False,
                metrics=[],
            ),
            id="scalar str",
        ),
        pytest.param(
            RawGraphTemplate(
                metrics=[],
                scalars=[("metric", "Title"), ("metric:warn", "Warn"), ("metric:crit", "Crit")],
            ),
            GraphTemplate(
                id="ident",
                title="",
                scalars=[
                    ScalarDefinition(
                        expression=Metric("metric"),
                        title="Title",
                    ),
                    ScalarDefinition(
                        expression=WarningOf(Metric("metric")),
                        title="Warn",
                    ),
                    ScalarDefinition(
                        expression=CriticalOf(Metric("metric")),
                        title="Crit",
                    ),
                ],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                range=None,
                omit_zero_metrics=False,
                metrics=[],
            ),
            id="scalar tuple",
        ),
        pytest.param(
            RawGraphTemplate(
                metrics=[("metric", "line")],
            ),
            GraphTemplate(
                id="ident",
                title="",
                scalars=[],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                range=None,
                omit_zero_metrics=False,
                metrics=[
                    MetricDefinition(
                        expression=Metric("metric"),
                        line_type="line",
                    ),
                ],
            ),
            id="metrics 2-er tuple",
        ),
        pytest.param(
            RawGraphTemplate(
                metrics=[("metric", "line", "Title")],
            ),
            GraphTemplate(
                id="ident",
                title="",
                scalars=[],
                conflicting_metrics=[],
                optional_metrics=[],
                consolidation_function=None,
                range=None,
                omit_zero_metrics=False,
                metrics=[
                    MetricDefinition(
                        expression=Metric("metric"),
                        line_type="line",
                        title="Title",
                    ),
                ],
            ),
            id="metrics 3-er tuple",
        ),
    ],
)
def test__graph_template_from_legacy(
    raw: RawGraphTemplate,
    expected_graph_template: GraphTemplate,
) -> None:
    assert _graph_template_from_legacy("ident", raw) == expected_graph_template


@pytest.mark.parametrize(
    "metric_names, check_command, graph_ids",
    [
        (["user", "system", "wait", "util"], "check_mk-kernel_util", ["cpu_utilization_5_util"]),
        (["util1", "util15"], "check_mk-kernel_util", ["util_average_2"]),
        (["util"], "check_mk-kernel_util", ["util_fallback"]),
        (["util"], "check_mk-lxc_container_cpu", ["util_fallback"]),
        (
            ["wait", "util", "user", "system"],
            "check_mk-lxc_container_cpu",
            ["cpu_utilization_5_util"],
        ),
        (["util", "util_average"], "check_mk-kernel_util", ["util_average_1"]),
        (["user", "util_numcpu_as_max"], "check_mk-kernel_util", ["cpu_utilization_numcpus"]),
        (
            ["user", "util"],
            "check_mk-kernel_util",
            ["util_fallback", "METRIC_user"],
        ),  # METRIC_user has no recipe
        (["user", "util"], "check_mk-winperf_processor_util", ["cpu_utilization_numcpus"]),
        (["user", "system", "idle", "nice"], "check_mk-kernel_util", ["cpu_utilization_3"]),
        (["user", "system", "idle", "io_wait"], "check_mk-kernel_util", ["cpu_utilization_4"]),
        (["user", "system", "io_wait"], "check_mk-kernel_util", ["cpu_utilization_5"]),
        (
            ["util_average", "util", "wait", "user", "system", "guest"],
            "check_mk-kernel_util",
            ["cpu_utilization_6_guest_util"],
        ),
        (
            ["user", "system", "io_wait", "guest", "steal"],
            "check_mk-statgrab_cpu",
            ["cpu_utilization_6_guest", "cpu_utilization_7"],
        ),
        (["user", "system", "interrupt"], "check_mk-kernel_util", ["cpu_utilization_8"]),
        (
            ["user", "system", "wait", "util", "cpu_entitlement", "cpu_entitlement_util"],
            "check_mk-lparstat_aix_cpu_util",
            ["cpu_entitlement", "cpu_utilization_5_util"],
        ),
        (
            ["ramused", "swapused", "memused"],
            "check_mk-statgrab_mem",
            ["METRIC_mem_lnx_total_used", "METRIC_mem_used", "METRIC_swap_used"],
        ),
        (
            [
                "aws_ec2_running_ondemand_instances_total",
                "aws_ec2_running_ondemand_instances_t2.micro",
                "aws_ec2_running_ondemand_instances_t2.nano",
            ],
            "check_mk-aws_ec2_limits",
            ["aws_ec2_running_ondemand_instances_t2", "aws_ec2_running_ondemand_instances"],
        ),
    ],
)
def test_get_graph_templates_1(
    metric_names: Sequence[str],
    check_command: str,
    graph_ids: Sequence[str],
    request_context: None,
) -> None:
    perfdata: Perfdata = [PerfDataTuple(n, n, 0, "", None, None, None, None) for n in metric_names]
    translated_metrics = translate_metrics(perfdata, check_command)
    assert sorted([t.id for t in get_graph_templates(translated_metrics)]) == sorted(graph_ids)


@pytest.mark.parametrize(
    "metric_names, warn_crit_min_max, check_command, graph_ids",
    [
        pytest.param(
            ["ramused", "swapused", "memused"],
            (0, 1, 2, 3),
            "check_mk-statgrab_mem",
            ["METRIC_mem_lnx_total_used", "ram_swap_used"],
            id="ram_swap_used",
        ),
    ],
)
def test_get_graph_templates_2(
    metric_names: Sequence[str],
    warn_crit_min_max: tuple[int, int, int, int],
    check_command: str,
    graph_ids: Sequence[str],
    request_context: None,
) -> None:
    perfdata: Perfdata = [PerfDataTuple(n, n, 0, "", *warn_crit_min_max) for n in metric_names]
    translated_metrics = translate_metrics(perfdata, check_command)
    assert sorted([t.id for t in get_graph_templates(translated_metrics)]) == sorted(graph_ids)


@pytest.mark.parametrize(
    "metric_definitions, expected_predictive_metric_definitions",
    [
        pytest.param(
            [],
            [],
            id="empty",
        ),
        pytest.param(
            [MetricDefinition(expression=Metric(name="metric_name"), line_type="line")],
            [
                MetricDefinition(expression=Metric(name="predict_metric_name"), line_type="line"),
                MetricDefinition(
                    expression=Metric(name="predict_lower_metric_name"), line_type="line"
                ),
            ],
            id="line",
        ),
        pytest.param(
            [MetricDefinition(expression=Metric(name="metric_name"), line_type="area")],
            [
                MetricDefinition(expression=Metric(name="predict_metric_name"), line_type="line"),
                MetricDefinition(
                    expression=Metric(name="predict_lower_metric_name"), line_type="line"
                ),
            ],
            id="area",
        ),
        pytest.param(
            [MetricDefinition(expression=Metric(name="metric_name"), line_type="stack")],
            [
                MetricDefinition(expression=Metric(name="predict_metric_name"), line_type="line"),
                MetricDefinition(
                    expression=Metric(name="predict_lower_metric_name"), line_type="line"
                ),
            ],
            id="stack",
        ),
        pytest.param(
            [MetricDefinition(expression=Metric(name="metric_name"), line_type="-line")],
            [
                MetricDefinition(expression=Metric(name="predict_metric_name"), line_type="-line"),
                MetricDefinition(
                    expression=Metric(name="predict_lower_metric_name"), line_type="-line"
                ),
            ],
            id="-line",
        ),
        pytest.param(
            [MetricDefinition(expression=Metric(name="metric_name"), line_type="-area")],
            [
                MetricDefinition(expression=Metric(name="predict_metric_name"), line_type="-line"),
                MetricDefinition(
                    expression=Metric(name="predict_lower_metric_name"), line_type="-line"
                ),
            ],
            id="-area",
        ),
        pytest.param(
            [MetricDefinition(expression=Metric(name="metric_name"), line_type="-stack")],
            [
                MetricDefinition(expression=Metric(name="predict_metric_name"), line_type="-line"),
                MetricDefinition(
                    expression=Metric(name="predict_lower_metric_name"), line_type="-line"
                ),
            ],
            id="-stack",
        ),
    ],
)
def test__compute_predictive_metrics(
    metric_definitions: Sequence[MetricDefinition],
    expected_predictive_metric_definitions: Sequence[MetricDefinition],
) -> None:
    assert (
        list(
            _compute_predictive_metrics(
                {
                    "metric_name": TranslatedMetric(
                        originals=[Original("metric_name", 1.0)],
                        value=0.0,
                        scalar={},
                        auto_graph=True,
                        title="",
                        unit_info=UnitInfo(
                            id="id",
                            title="Title",
                            symbol="",
                            render=lambda v: f"{v}",
                            js_render="v => v",
                            conversion=lambda v: v,
                        ),
                        color="#0080c0",
                    ),
                    "predict_metric_name": TranslatedMetric(
                        originals=[Original("predict_metric_name", 1.0)],
                        value=0.0,
                        scalar={},
                        auto_graph=True,
                        title="",
                        unit_info=UnitInfo(
                            id="id",
                            title="Title",
                            symbol="",
                            render=lambda v: f"{v}",
                            js_render="v => v",
                            conversion=lambda v: v,
                        ),
                        color="#0080c0",
                    ),
                    "predict_lower_metric_name": TranslatedMetric(
                        originals=[Original("predict_lower_metric_name", 1.0)],
                        value=0.0,
                        scalar={},
                        auto_graph=True,
                        title="",
                        unit_info=UnitInfo(
                            id="id",
                            title="Title",
                            symbol="",
                            render=lambda v: f"{v}",
                            js_render="v => v",
                            conversion=lambda v: v,
                        ),
                        color="#0080c0",
                    ),
                },
                metric_definitions,
            )
        )
        == expected_predictive_metric_definitions
    )


@pytest.mark.parametrize(
    "metric_names, predict_metric_names, predict_lower_metric_names, check_command, graph_templates",
    [
        pytest.param(
            [
                "messages_outbound",
                "messages_inbound",
            ],
            [
                "predict_messages_outbound",
                "predict_messages_inbound",
            ],
            [
                "predict_lower_messages_outbound",
                "predict_lower_messages_inbound",
            ],
            "check_mk-inbound_and_outbound_messages",
            [
                GraphTemplate(
                    id="inbound_and_outbound_messages",
                    title="Inbound and Outbound Messages",
                    scalars=[],
                    conflicting_metrics=(),
                    optional_metrics=(),
                    consolidation_function=None,
                    range=None,
                    omit_zero_metrics=False,
                    metrics=[
                        MetricDefinition(
                            expression=Metric(name="messages_outbound"),
                            line_type="stack",
                            title="Outbound messages",
                        ),
                        MetricDefinition(
                            expression=Metric(name="messages_inbound"),
                            line_type="stack",
                            title="Inbound messages",
                        ),
                        MetricDefinition(
                            expression=Metric(name="predict_messages_outbound"),
                            line_type="line",
                        ),
                        MetricDefinition(
                            expression=Metric(name="predict_lower_messages_outbound"),
                            line_type="line",
                        ),
                        MetricDefinition(
                            expression=Metric(name="predict_messages_inbound"),
                            line_type="line",
                        ),
                        MetricDefinition(
                            expression=Metric(name="predict_lower_messages_inbound"),
                            line_type="line",
                        ),
                    ],
                )
            ],
            id="matches",
        ),
        pytest.param(
            [
                "messages_outbound",
                "messages_inbound",
                "foo",
            ],
            [
                "predict_foo",
            ],
            [
                "predict_lower_foo",
            ],
            "check_mk-inbound_and_outbound_messages",
            [
                GraphTemplate(
                    id="inbound_and_outbound_messages",
                    title="Inbound and Outbound Messages",
                    scalars=[],
                    conflicting_metrics=(),
                    optional_metrics=(),
                    consolidation_function=None,
                    range=None,
                    omit_zero_metrics=False,
                    metrics=[
                        MetricDefinition(
                            expression=Metric(name="messages_outbound"),
                            line_type="stack",
                            title="Outbound messages",
                        ),
                        MetricDefinition(
                            expression=Metric(name="messages_inbound"),
                            line_type="stack",
                            title="Inbound messages",
                        ),
                    ],
                ),
                GraphTemplate(
                    id="METRIC_foo",
                    title="",
                    scalars=[
                        ScalarDefinition(
                            expression=WarningOf(metric=Metric(name="foo")),
                            title="Warning",
                        ),
                        ScalarDefinition(
                            expression=CriticalOf(metric=Metric(name="foo")),
                            title="Critical",
                        ),
                    ],
                    conflicting_metrics=[],
                    optional_metrics=[],
                    consolidation_function=None,
                    range=None,
                    omit_zero_metrics=False,
                    metrics=[
                        MetricDefinition(
                            expression=Metric(name="foo"),
                            line_type="area",
                        )
                    ],
                ),
                GraphTemplate(
                    id="METRIC_predict_foo",
                    title="",
                    scalars=[
                        ScalarDefinition(
                            expression=WarningOf(metric=Metric(name="predict_foo")),
                            title="Warning",
                        ),
                        ScalarDefinition(
                            expression=CriticalOf(metric=Metric(name="predict_foo")),
                            title="Critical",
                        ),
                    ],
                    conflicting_metrics=[],
                    optional_metrics=[],
                    consolidation_function=None,
                    range=None,
                    omit_zero_metrics=False,
                    metrics=[
                        MetricDefinition(
                            expression=Metric(name="predict_foo"),
                            line_type="area",
                        )
                    ],
                ),
                GraphTemplate(
                    id="METRIC_predict_lower_foo",
                    title="",
                    scalars=[
                        ScalarDefinition(
                            expression=WarningOf(metric=Metric(name="predict_lower_foo")),
                            title="Warning",
                        ),
                        ScalarDefinition(
                            expression=CriticalOf(metric=Metric(name="predict_lower_foo")),
                            title="Critical",
                        ),
                    ],
                    conflicting_metrics=[],
                    optional_metrics=[],
                    consolidation_function=None,
                    range=None,
                    omit_zero_metrics=False,
                    metrics=[
                        MetricDefinition(
                            expression=Metric(name="predict_lower_foo"),
                            line_type="area",
                        )
                    ],
                ),
            ],
            id="does-not-match",
        ),
    ],
)
def test_get_graph_templates_with_predictive_metrics(
    metric_names: Sequence[str],
    predict_metric_names: Sequence[str],
    predict_lower_metric_names: Sequence[str],
    check_command: str,
    graph_templates: Sequence[GraphTemplate],
    request_context: None,
) -> None:
    perfdata: Perfdata = (
        [PerfDataTuple(n, n, 0, "", None, None, None, None) for n in metric_names]
        + [PerfDataTuple(n, n[8:], 0, "", None, None, None, None) for n in predict_metric_names]
        + [
            PerfDataTuple(n, n[14:], 0, "", None, None, None, None)
            for n in predict_lower_metric_names
        ]
    )
    translated_metrics = translate_metrics(perfdata, check_command)
    found_graph_templates = list(get_graph_templates(translated_metrics))
    assert found_graph_templates == graph_templates


@pytest.mark.parametrize(
    "metric_names, graph_ids",
    [
        # cpu.py
        pytest.param(
            ["user_time", "children_user_time", "system_time", "children_system_time"],
            ["used_cpu_time"],
            id="used_cpu_time",
        ),
        pytest.param(
            [
                "user_time",
                "children_user_time",
                "system_time",
                "children_system_time",
                "cmk_time_agent",
                "cmk_time_snmp",
                "cmk_time_ds",
            ],
            [
                "METRIC_children_system_time",
                "METRIC_children_user_time",
                "METRIC_cmk_time_agent",
                "METRIC_cmk_time_ds",
                "METRIC_cmk_time_snmp",
                "METRIC_system_time",
                "METRIC_user_time",
            ],
            id="used_cpu_time_conflicting_metrics",
        ),
        pytest.param(
            ["user_time", "system_time"],
            ["cpu_time"],
            id="cpu_time",
        ),
        pytest.param(
            ["user_time", "system_time", "children_user_time"],
            ["METRIC_children_user_time", "METRIC_system_time", "METRIC_user_time"],
            id="cpu_time_conflicting_metrics",
        ),
        pytest.param(
            ["util", "util_average"],
            ["util_average_1"],
            id="util_average_1",
        ),
        pytest.param(
            [
                "util",
                "util_average",
                "util_average_1",
                "idle",
                "cpu_util_guest",
                "cpu_util_steal",
                "io_wait",
                "user",
                "system",
            ],
            ["cpu_utilization_4", "cpu_utilization_7_util", "METRIC_util_average_1"],
            id="util_average_1_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "util_average", "util"],
            ["cpu_utilization_simple"],
            id="cpu_utilization_simple",
        ),
        pytest.param(
            [
                "user",
                "system",
                "util_average",
                "util",
                "idle",
                "cpu_util_guest",
                "cpu_util_steal",
                "io_wait",
            ],
            ["cpu_utilization_4", "cpu_utilization_7_util"],
            id="cpu_utilization_simple_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "util_average"],
            ["cpu_utilization_5"],
            id="cpu_utilization_5",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "util_average",
                "util",
                "idle",
                "cpu_util_guest",
                "cpu_util_steal",
            ],
            ["cpu_utilization_4", "cpu_utilization_7_util"],
            id="cpu_utilization_5_conflicting_metrics",
        ),
        # cpu_utilization_5_util
        pytest.param(
            ["user", "system", "io_wait", "util_average", "util"],
            ["cpu_utilization_5_util"],
            id="cpu_utilization_5_util",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "util_average",
                "util",
                "cpu_util_guest",
                "cpu_util_steal",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_5_util_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_steal", "util_average"],
            ["cpu_utilization_6_steal"],
            id="cpu_utilization_6_steal",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_steal",
                "util_average",
                "util",
                "cpu_util_guest",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_steal_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_steal", "util_average", "util"],
            ["cpu_utilization_6_steal_util"],
            id="cpu_utilization_6_steal_util",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_steal",
                "util_average",
                "util",
                "cpu_util_guest",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_steal_util_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "util_average", "cpu_util_steal"],
            ["cpu_utilization_6_guest", "cpu_utilization_7"],
            id="cpu_utilization_6_guest",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_guest",
                "util_average",
                "cpu_util_steal",
                "util",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_guest_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "util_average", "util"],
            ["cpu_utilization_6_guest_util"],
            id="cpu_utilization_6_guest_util",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_guest",
                "util_average",
                "util",
                "cpu_util_steal",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_guest_util_conflicting_metrics",
        ),
        #
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "cpu_util_steal", "util_average"],
            ["cpu_utilization_6_guest", "cpu_utilization_7"],
            id="cpu_utilization_7",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_guest",
                "cpu_util_steal",
                "util_average",
                "util",
            ],
            ["cpu_utilization_7_util"],
            id="cpu_utilization_7_conflicting_metrics",
        ),
        pytest.param(
            ["util"],
            ["util_fallback"],
            id="util_fallback",
        ),
        pytest.param(
            ["util", "util_average", "system", "engine_cpu_util"],
            ["cpu_utilization", "METRIC_system", "METRIC_util_average"],
            id="util_fallback_conflicting_metrics",
        ),
        # fs.py
        pytest.param(
            ["fs_used", "fs_size"],
            ["fs_used"],
            id="fs_used",
        ),
        pytest.param(
            ["fs_used", "fs_size", "reserved"],
            ["METRIC_fs_size", "METRIC_fs_used", "METRIC_reserved"],
            id="fs_used_conflicting_metrics",
        ),
        # mail.py
        pytest.param(
            ["mail_queue_deferred_length", "mail_queue_active_length"],
            ["amount_of_mails_in_queues"],
            id="amount_of_mails_in_queues",
        ),
        pytest.param(
            [
                "mail_queue_deferred_length",
                "mail_queue_active_length",
                "mail_queue_postfix_total",
                "mail_queue_z1_messenger",
            ],
            [
                "METRIC_mail_queue_active_length",
                "METRIC_mail_queue_deferred_length",
                "METRIC_mail_queue_postfix_total",
                "METRIC_mail_queue_z1_messenger",
            ],
            id="amount_of_mails_in_queues_conflicting_metrics",
        ),
        pytest.param(
            ["mail_queue_deferred_size", "mail_queue_active_size"],
            ["size_of_mails_in_queues"],
            id="size_of_mails_in_queues",
        ),
        pytest.param(
            [
                "mail_queue_deferred_size",
                "mail_queue_active_size",
                "mail_queue_postfix_total",
                "mail_queue_z1_messenger",
            ],
            [
                "METRIC_mail_queue_active_size",
                "METRIC_mail_queue_deferred_size",
                "METRIC_mail_queue_postfix_total",
                "METRIC_mail_queue_z1_messenger",
            ],
            id="size_of_mails_in_queues_conflicting_metrics",
        ),
        pytest.param(
            ["mail_queue_hold_length", "mail_queue_incoming_length", "mail_queue_drop_length"],
            ["amount_of_mails_in_secondary_queues"],
            id="amount_of_mails_in_secondary_queues",
        ),
        pytest.param(
            [
                "mail_queue_hold_length",
                "mail_queue_incoming_length",
                "mail_queue_drop_length",
                "mail_queue_postfix_total",
                "mail_queue_z1_messenger",
            ],
            [
                "METRIC_mail_queue_drop_length",
                "METRIC_mail_queue_hold_length",
                "METRIC_mail_queue_incoming_length",
                "METRIC_mail_queue_postfix_total",
                "METRIC_mail_queue_z1_messenger",
            ],
            id="amount_of_mails_in_secondary_queues_conflicting_metrics",
        ),
        # storage.py
        pytest.param(
            ["mem_used", "swap_used"],
            ["METRIC_mem_used", "METRIC_swap_used"],
            id="ram_used_conflicting_metrics",
        ),
        pytest.param(
            ["mem_used", "swap_used", "swap_total"],
            ["METRIC_mem_used", "METRIC_swap_total", "METRIC_swap_used"],
            id="ram_swap_used_conflicting_metrics",
        ),
        pytest.param(
            ["mem_lnx_active", "mem_lnx_inactive"],
            ["active_and_inactive_memory"],
            id="active_and_inactive_memory",
        ),
        pytest.param(
            ["mem_lnx_active", "mem_lnx_inactive", "mem_lnx_active_anon"],
            [
                "METRIC_mem_lnx_active",
                "METRIC_mem_lnx_active_anon",
                "METRIC_mem_lnx_inactive",
            ],
            id="active_and_inactive_memory_conflicting_metrics",
        ),
        pytest.param(
            ["mem_used"],
            ["ram_used"],
            id="ram_used",
        ),
        pytest.param(
            ["mem_heap", "mem_nonheap"],
            ["heap_and_non_heap_memory"],
            id="heap_and_non_heap_memory",
        ),
        pytest.param(
            ["mem_heap", "mem_nonheap", "mem_heap_committed", "mem_nonheap_committed"],
            ["heap_memory_usage", "non-heap_memory_usage"],
            id="heap_and_non_heap_memory_conflicting_metrics",
        ),
    ],
)
def test_conflicting_metrics(
    metric_names: Sequence[str],
    graph_ids: Sequence[str],
    request_context: None,
) -> None:
    # Hard to find all avail metric names of a check plug-in.
    # We test conflicting metrics as following:
    # 1. write test for expected metric names of a graph template if it has "conflicting_metrics"
    # 2. use metric names from (1) and conflicting metrics
    perfdata: Perfdata = [PerfDataTuple(n, n, 0, "", None, None, None, None) for n in metric_names]
    translated_metrics = translate_metrics(perfdata, "check_command")
    assert sorted([t.id for t in get_graph_templates(translated_metrics)]) == sorted(graph_ids)
