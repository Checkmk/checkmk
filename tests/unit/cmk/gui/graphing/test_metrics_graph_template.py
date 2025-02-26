#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import SiteId

from cmk.utils.hostaddress import HostName

import cmk.gui.graphing._graph_templates as gt
from cmk.gui.config import active_config
from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._graph_specification import GraphMetric, GraphRecipe, MinimalVerticalRange
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification
from cmk.gui.graphing._metric_expression import parse_legacy_expression
from cmk.gui.graphing._metric_operation import (
    MetricOpConstant,
    MetricOperation,
    MetricOpOperator,
    MetricOpRRDSource,
)
from cmk.gui.graphing._translated_metrics import parse_perf_data, translate_metrics
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, IECNotation
from cmk.gui.type_defs import Row


@pytest.mark.parametrize(
    "raw_expression, result",
    [
        (
            "fs_size,fs_used,-",
            MetricOpOperator(
                operator_name="-",
                operands=[
                    MetricOpRRDSource(
                        site_id=SiteId(""),
                        host_name=HostName(""),
                        service_name="",
                        metric_name="fs_size",
                        consolidation_func_name=None,
                        scale=1048576,
                    ),
                    MetricOpRRDSource(
                        site_id=SiteId(""),
                        host_name=HostName(""),
                        service_name="",
                        metric_name="_",
                        consolidation_func_name=None,
                        scale=1048576,
                    ),
                ],
            ),
        ),
        (
            "fs_growth.min,0,MIN,-1,*",
            MetricOpOperator(
                operator_name="*",
                operands=[
                    MetricOpOperator(
                        operator_name="MIN",
                        operands=[
                            MetricOpRRDSource(
                                site_id=SiteId(""),
                                host_name=HostName(""),
                                service_name="",
                                metric_name="growth",
                                consolidation_func_name="min",
                                scale=12.136296296296296,
                            ),
                            MetricOpConstant(value=0.0),
                        ],
                    ),
                    MetricOpConstant(value=-1.0),
                ],
            ),
        ),
    ],
)
def test_rpn_stack(raw_expression: str, result: MetricOperation) -> None:
    perf_data, check_command = parse_perf_data(
        "/=163651.992188;;;; fs_size=477500.03125;;;; growth=-1280.489081;;;;",
        "check_mk-df",
        config=active_config,
    )
    translated_metrics = translate_metrics(perf_data, check_command)
    assert (
        gt.metric_expression_to_graph_recipe_expression(
            SiteId(""),
            HostName(""),
            "",
            parse_legacy_expression(raw_expression, "line", "", translated_metrics).base,
            translated_metrics,
            None,
        )
        == result
    )


class FakeTemplateGraphSpecification(TemplateGraphSpecification):
    def _get_graph_data_from_livestatus(self) -> Row:
        return {
            "site": "site_id",
            "service_perf_data": "fs_used=163651.992188;;;; fs_free=313848.039062;;; fs_size=477500.03125;;;; growth=-1280.489081;;;;",
            "service_metrics": ["fs_used", "fs_free", "fs_size", "growth"],
            "service_check_command": "check_mk-df",
            "host_name": "host_name",
            "service_description": "Service name",
        }


def test_template_recipes() -> None:
    assert FakeTemplateGraphSpecification(
        site=SiteId("site_id"),
        host_name=HostName("host_name"),
        service_description="Service name",
    ).recipes() == [
        GraphRecipe(
            title="Size and used space",
            unit_spec=ConvertibleUnitSpecification(
                notation=IECNotation(symbol="B"),
                precision=AutoPrecision(digits=2),
            ),
            explicit_vertical_range=MinimalVerticalRange(min=0.0, max=None),
            horizontal_rules=[],
            omit_zero_metrics=False,
            consolidation_function="max",
            metrics=[
                GraphMetric(
                    title="Used space",
                    line_type="stack",
                    operation=MetricOpRRDSource(
                        site_id=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_name="Service name",
                        metric_name="fs_used",
                        consolidation_func_name="max",
                        scale=1048576.0,
                    ),
                    unit=ConvertibleUnitSpecification(
                        notation=IECNotation(symbol="B"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1e90ff",
                ),
                GraphMetric(
                    title="Free space",
                    line_type="stack",
                    operation=MetricOpRRDSource(
                        site_id=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_name="Service name",
                        metric_name="fs_free",
                        consolidation_func_name="max",
                        scale=1048576.0,
                    ),
                    unit=ConvertibleUnitSpecification(
                        notation=IECNotation(symbol="B"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#d28df6",
                ),
                GraphMetric(
                    title="Total size",
                    line_type="line",
                    operation=MetricOpRRDSource(
                        site_id=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_name="Service name",
                        metric_name="fs_size",
                        consolidation_func_name="max",
                        scale=1048576.0,
                    ),
                    unit=ConvertibleUnitSpecification(
                        notation=IECNotation(symbol="B"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#37fa37",
                ),
            ],
            additional_html=None,
            data_range=None,
            mark_requested_end_time=False,
            specification=FakeTemplateGraphSpecification(
                site=SiteId("site_id"),
                host_name=HostName("host_name"),
                service_description="Service name",
                graph_index=0,
                graph_id="fs_used",
                destination=None,
            ),
        ),
        GraphRecipe(
            title="Growth",
            unit_spec=ConvertibleUnitSpecification(
                notation=IECNotation(symbol="B/d"),
                precision=AutoPrecision(digits=2),
            ),
            explicit_vertical_range=None,
            horizontal_rules=[],
            omit_zero_metrics=False,
            consolidation_function="max",
            metrics=[
                GraphMetric(
                    title="Growth",
                    line_type="area",
                    operation=MetricOpRRDSource(
                        site_id=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_name="Service name",
                        metric_name="growth",
                        consolidation_func_name="max",
                        scale=12.136296296296296,
                    ),
                    unit=ConvertibleUnitSpecification(
                        notation=IECNotation(symbol="B/d"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1ee6e6",
                )
            ],
            additional_html=None,
            data_range=None,
            mark_requested_end_time=False,
            specification=FakeTemplateGraphSpecification(
                site=SiteId("site_id"),
                host_name=HostName("host_name"),
                service_description="Service name",
                graph_index=1,
                graph_id="METRIC_fs_growth",
                destination=None,
            ),
        ),
    ]


@pytest.mark.parametrize(
    "expression, perf_data_string, check_command, result_color",
    [
        (
            "load15",
            "load1=0.38;40;80;0;8 load5=0.62;40;80;0;8 load15=0.68;40;80;0;8",
            "check_mk-cpu.loads",
            "#1873cc",
        ),
        ("test", "test=5;5;10;0;20", "check_mk-local", "#cc00ff"),
    ],
)
def test_metric_unit_color(
    expression: str, perf_data_string: str, check_command: str | None, result_color: str
) -> None:
    perf_data, check_command = parse_perf_data(
        perf_data_string, check_command, config=active_config
    )
    translated_metrics = translate_metrics(perf_data, check_command)
    translated_metric = translated_metrics.get(expression)
    assert translated_metric is not None
    evaluated = parse_legacy_expression(expression, "line", "", translated_metrics).evaluate(
        translated_metrics
    )
    assert evaluated.is_ok()
    assert evaluated.ok.unit_spec == (
        translated_metric.unit_spec
        if isinstance(translated_metric.unit_spec, ConvertibleUnitSpecification)
        else translated_metric.unit_spec.id
    )
    assert evaluated.ok.color == result_color


@pytest.mark.parametrize(
    "expression, perf_data_string, check_command",
    [
        ("test", "", "check_mk-local"),
    ],
)
def test_metric_unit_color_skip(
    expression: str, perf_data_string: str, check_command: str | None
) -> None:
    perf_data, check_command = parse_perf_data(
        perf_data_string, check_command, config=active_config
    )
    translated_metrics = translate_metrics(perf_data, check_command)
    evaluated = parse_legacy_expression(expression, "line", "", translated_metrics).evaluate(
        translated_metrics
    )
    assert evaluated.is_error()
    assert evaluated.error.metric_name == "test"


@pytest.mark.parametrize(
    "expression, perf_data_string, check_command",
    [
        ("level,altitude,+", "test=5;5;10;0;20", "check_mk-local"),
    ],
)
def test_metric_unit_color_exception(
    expression: str, perf_data_string: str, check_command: str | None
) -> None:
    perf_data, check_command = parse_perf_data(
        perf_data_string, check_command, config=active_config
    )
    translated_metrics = translate_metrics(perf_data, check_command)
    evaluated = parse_legacy_expression(expression, "line", "", translated_metrics).evaluate(
        translated_metrics
    )
    assert evaluated.is_error()
    assert evaluated.error.metric_name == "level"
