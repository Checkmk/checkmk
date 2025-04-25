#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._from_api import RegisteredMetric
from cmk.gui.graphing._graph_specification import GraphMetric, GraphRecipe, MinimalVerticalRange
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification
from cmk.gui.graphing._metric_operation import MetricOpRRDSource
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, IECNotation
from cmk.gui.type_defs import Row

from cmk.graphing.v1 import graphs, metrics, Title


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
    ).recipes(
        {
            "fs_growth": RegisteredMetric(
                name="fs_growth",
                title_localizer=lambda _localizer: "Growth",
                unit_spec=ConvertibleUnitSpecification(
                    notation=IECNotation(symbol="B/d"),
                    precision=AutoPrecision(digits=2),
                ),
                color="#1ee6e6",
            ),
            "fs_used": RegisteredMetric(
                name="fs_used",
                title_localizer=lambda _localizer: "Used space",
                unit_spec=ConvertibleUnitSpecification(
                    notation=IECNotation(symbol="B"),
                    precision=AutoPrecision(digits=2),
                ),
                color="#1e90ff",
            ),
            "fs_free": RegisteredMetric(
                name="fs_free",
                title_localizer=lambda _localizer: "Free space",
                unit_spec=ConvertibleUnitSpecification(
                    notation=IECNotation(symbol="B"),
                    precision=AutoPrecision(digits=2),
                ),
                color="#d28df6",
            ),
            "fs_size": RegisteredMetric(
                name="fs_size",
                title_localizer=lambda _localizer: "Total size",
                unit_spec=ConvertibleUnitSpecification(
                    notation=IECNotation(symbol="B"),
                    precision=AutoPrecision(digits=2),
                ),
                color="#37fa37",
            ),
        },
        {
            "fs_used": graphs.Graph(
                name="fs_used",
                title=Title("Size and used space"),
                minimal_range=graphs.MinimalRange(
                    0,
                    metrics.MaximumOf(
                        "fs_used",
                        metrics.Color.GRAY,
                    ),
                ),
                compound_lines=[
                    "fs_used",
                    "fs_free",
                ],
                simple_lines=[
                    "fs_size",
                    metrics.WarningOf("fs_used"),
                    metrics.CriticalOf("fs_used"),
                ],
                conflicting=["reserved"],
            ),
        },
    ) == [
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
