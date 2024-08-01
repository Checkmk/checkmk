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
from cmk.gui.graphing._expression import Constant, CriticalOf, Metric, Product, WarningOf
from cmk.gui.graphing._graph_specification import (
    HorizontalRule,
    MetricOpOperator,
    MetricOpRRDSource,
)
from cmk.gui.graphing._graph_templates import _matching_graph_templates
from cmk.gui.graphing._graph_templates_from_plugins import (
    _graph_templates_from_plugins,
    _parse_graph_template,
    GraphTemplate,
    ScalarDefinition,
)
from cmk.gui.graphing._legacy import UnitInfo
from cmk.gui.graphing._type_defs import TranslatedMetric
from cmk.gui.graphing._utils import parse_perf_data, translate_metrics
from cmk.gui.type_defs import Perfdata, PerfDataTuple

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
                HorizontalRule(7.0, "7.00", "#ffd000", "Warning"),
                HorizontalRule(10.0, "10 W", "#ff3232", "Critical power"),
                HorizontalRule(-2.0, "-2.00", "#ffd000", "Warning output"),
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
                service_name="Service Description",
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
                        service_name="Service Description",
                        metric_name="metric-name",
                        consolidation_func_name=None,
                        scale=1.0,
                    ),
                    MetricOpRRDSource(
                        site_id=SiteId("Site-ID"),
                        host_name=HostName("HostName"),
                        service_name="Service Description",
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
            Metric("metric-name"),
            {
                "metric-name": TranslatedMetric(
                    orig_name=list(orig_names),
                    value=23.5,
                    scalar={},
                    scale=list(scales),
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
            {
                "site": "Site-ID",
                "host_name": "HostName",
                "service_description": "Service Description",
            },
            None,
        )
        == expected_operation
    )
