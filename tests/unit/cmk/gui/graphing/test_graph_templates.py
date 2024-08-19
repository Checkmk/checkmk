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
from cmk.gui.graphing._from_api import metrics_from_api
from cmk.gui.graphing._graph_specification import (
    HorizontalRule,
    MetricOpOperator,
    MetricOpRRDSource,
)
from cmk.gui.graphing._graph_templates import (
    _graph_template_from_api_bidirectional,
    _graph_template_from_api_graph,
    _graph_template_from_legacy,
    _graph_templates_from_plugins,
    _matching_graph_templates,
    _parse_graph_template,
    GraphTemplate,
    MetricDefinition,
    MinimalGraphTemplateRange,
    ScalarDefinition,
)
from cmk.gui.graphing._legacy import RawGraphTemplate, UnitInfo
from cmk.gui.graphing._type_defs import Original, TranslatedMetric
from cmk.gui.graphing._utils import parse_perf_data, translate_metrics
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
            tuple(sorted(m.name for e in expressions for m in e.metrics())), []
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
                            explicit_unit_id="DecimalNotation__AutoPrecision_2",
                            explicit_color=COLOR_HEX,
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
                            explicit_color=COLOR_HEX,
                        ),
                        "stack",
                        "Title",
                    ),
                    MetricDefinition(
                        MaximumOf(
                            Metric("metric-name-5"),
                            explicit_color=COLOR_HEX,
                        ),
                        "stack",
                        "Title",
                    ),
                    MetricDefinition(
                        Sum(
                            [Metric("metric-name-6")],
                            explicit_color=COLOR_HEX,
                        ),
                        "stack",
                        "Sum",
                    ),
                    MetricDefinition(
                        Product(
                            [Metric("metric-name-7")],
                            explicit_unit_id="DecimalNotation__AutoPrecision_2",
                            explicit_color=COLOR_HEX,
                        ),
                        "stack",
                        "Product",
                    ),
                    MetricDefinition(
                        Difference(
                            minuend=Metric("metric-name-7"),
                            subtrahend=Metric("metric-name-8"),
                            explicit_color=COLOR_HEX,
                        ),
                        "stack",
                        "Difference",
                    ),
                    MetricDefinition(
                        Fraction(
                            dividend=Metric("metric-name-9"),
                            divisor=Metric("metric-name-10"),
                            explicit_unit_id="DecimalNotation__AutoPrecision_2",
                            explicit_color=COLOR_HEX,
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
                            explicit_color=COLOR_HEX,
                        ),
                        "Title",
                    ),
                    ScalarDefinition(
                        MaximumOf(
                            Metric("metric-name-5"),
                            explicit_color=COLOR_HEX,
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
                            explicit_unit_id="DecimalNotation__AutoPrecision_2",
                            explicit_color=COLOR_HEX,
                        ),
                        "line",
                        "Constant",
                    ),
                    MetricDefinition(
                        Sum(
                            [Metric("metric-name-6")],
                            explicit_color=COLOR_HEX,
                        ),
                        "line",
                        "Sum",
                    ),
                    MetricDefinition(
                        Product(
                            [Metric("metric-name-7")],
                            explicit_unit_id="DecimalNotation__AutoPrecision_2",
                            explicit_color=COLOR_HEX,
                        ),
                        "line",
                        "Product",
                    ),
                    MetricDefinition(
                        Difference(
                            minuend=Metric("metric-name-7"),
                            subtrahend=Metric("metric-name-8"),
                            explicit_color=COLOR_HEX,
                        ),
                        "line",
                        "Difference",
                    ),
                    MetricDefinition(
                        Fraction(
                            dividend=Metric("metric-name-9"),
                            divisor=Metric("metric-name-10"),
                            explicit_unit_id="DecimalNotation__AutoPrecision_2",
                            explicit_color=COLOR_HEX,
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
            metrics_api.Metric(
                name=r,
                title=Title("Title"),
                unit=metrics_api.Unit(metrics_api.DecimalNotation("")),
                color=metrics_api.Color.BLUE,
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
                        MinimumOf(Metric("metric-name-l5"), explicit_color=COLOR_HEX),
                        "Title",
                    ),
                    ScalarDefinition(
                        MaximumOf(Metric("metric-name-l6"), explicit_color=COLOR_HEX),
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
                        MinimumOf(Metric("metric-name-u5"), explicit_color=COLOR_HEX),
                        "Title",
                    ),
                    ScalarDefinition(
                        MaximumOf(Metric("metric-name-u6"), explicit_color=COLOR_HEX),
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
            metrics_api.Metric(
                name=r,
                title=Title("Title"),
                unit=metrics_api.Unit(metrics_api.DecimalNotation("")),
                color=metrics_api.Color.BLUE,
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
