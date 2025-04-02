#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import SiteId

from cmk.utils.hostaddress import HostName

from cmk.gui.graphing._graph_specification import (
    GraphMetric,
    GraphRecipe,
    MetricOpOperator,
    MetricOpRRDSource,
)
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification


def test_graph_recipe_dump() -> None:
    assert GraphRecipe(
        title="Time usage by phase",
        unit="s",
        explicit_vertical_range=None,
        horizontal_rules=[],
        omit_zero_metrics=False,
        consolidation_function="max",
        metrics=[
            GraphMetric(
                title="CPU time in user space",
                line_type="stack",
                operation=MetricOpOperator(
                    ident="operator",
                    operator_name="+",
                    operands=[
                        MetricOpRRDSource(
                            ident="rrd",
                            site_id=SiteId("stable"),
                            host_name=HostName("stable"),
                            service_name="Check_MK",
                            metric_name="user_time",
                            consolidation_func_name="max",
                            scale=1.0,
                        ),
                        MetricOpRRDSource(
                            ident="rrd",
                            site_id=SiteId("stable"),
                            host_name=HostName("stable"),
                            service_name="Check_MK",
                            metric_name="children_user_time",
                            consolidation_func_name="max",
                            scale=1.0,
                        ),
                    ],
                ),
                unit="s",
                color="#87f058",
                visible=True,
            ),
            GraphMetric(
                title="CPU time in operating system",
                line_type="stack",
                operation=MetricOpOperator(
                    ident="operator",
                    operator_name="+",
                    operands=[
                        MetricOpRRDSource(
                            ident="rrd",
                            site_id=SiteId("stable"),
                            host_name=HostName("stable"),
                            service_name="Check_MK",
                            metric_name="system_time",
                            consolidation_func_name="max",
                            scale=1.0,
                        ),
                        MetricOpRRDSource(
                            ident="rrd",
                            site_id=SiteId("stable"),
                            host_name=HostName("stable"),
                            service_name="Check_MK",
                            metric_name="children_system_time",
                            consolidation_func_name="max",
                            scale=1.0,
                        ),
                    ],
                ),
                unit="s",
                color="#ff8840",
                visible=True,
            ),
            GraphMetric(
                title="Time spent waiting for Checkmk agent",
                line_type="stack",
                operation=MetricOpRRDSource(
                    ident="rrd",
                    site_id=SiteId("stable"),
                    host_name=HostName("stable"),
                    service_name="Check_MK",
                    metric_name="cmk_time_agent",
                    consolidation_func_name="max",
                    scale=1.0,
                ),
                unit="s",
                color="#0093ff",
                visible=True,
            ),
            GraphMetric(
                title="Total execution time",
                line_type="line",
                operation=MetricOpRRDSource(
                    ident="rrd",
                    site_id=SiteId("stable"),
                    host_name=HostName("stable"),
                    service_name="Check_MK",
                    metric_name="execution_time",
                    consolidation_func_name="max",
                    scale=1.0,
                ),
                unit="s",
                color="#d080af",
                visible=True,
            ),
        ],
        additional_html=None,
        render_options={},
        data_range=None,
        mark_requested_end_time=False,
        specification=TemplateGraphSpecification(
            graph_type="template",
            site=SiteId("stable"),
            host_name=HostName("stable"),
            service_description="Check_MK",
            graph_index=0,
            graph_id="cmk_cpu_time_by_phase",
            destination=None,
        ),
    ).model_dump() == {
        "title": "Time usage by phase",
        "unit": "s",
        "explicit_vertical_range": None,
        "horizontal_rules": [],
        "omit_zero_metrics": False,
        "consolidation_function": "max",
        "metrics": [
            {
                "title": "CPU time in user space",
                "line_type": "stack",
                "operation": {
                    "ident": "operator",
                    "operator_name": "+",
                    "operands": [
                        {
                            "ident": "rrd",
                            "site_id": "stable",
                            "host_name": "stable",
                            "service_name": "Check_MK",
                            "metric_name": "user_time",
                            "consolidation_func_name": "max",
                            "scale": 1.0,
                        },
                        {
                            "ident": "rrd",
                            "site_id": "stable",
                            "host_name": "stable",
                            "service_name": "Check_MK",
                            "metric_name": "children_user_time",
                            "consolidation_func_name": "max",
                            "scale": 1.0,
                        },
                    ],
                },
                "unit": "s",
                "color": "#87f058",
                "visible": True,
            },
            {
                "title": "CPU time in operating system",
                "line_type": "stack",
                "operation": {
                    "ident": "operator",
                    "operator_name": "+",
                    "operands": [
                        {
                            "ident": "rrd",
                            "site_id": "stable",
                            "host_name": "stable",
                            "service_name": "Check_MK",
                            "metric_name": "system_time",
                            "consolidation_func_name": "max",
                            "scale": 1.0,
                        },
                        {
                            "ident": "rrd",
                            "site_id": "stable",
                            "host_name": "stable",
                            "service_name": "Check_MK",
                            "metric_name": "children_system_time",
                            "consolidation_func_name": "max",
                            "scale": 1.0,
                        },
                    ],
                },
                "unit": "s",
                "color": "#ff8840",
                "visible": True,
            },
            {
                "title": "Time spent waiting for Checkmk agent",
                "line_type": "stack",
                "operation": {
                    "ident": "rrd",
                    "site_id": "stable",
                    "host_name": "stable",
                    "service_name": "Check_MK",
                    "metric_name": "cmk_time_agent",
                    "consolidation_func_name": "max",
                    "scale": 1.0,
                },
                "unit": "s",
                "color": "#0093ff",
                "visible": True,
            },
            {
                "title": "Total execution time",
                "line_type": "line",
                "operation": {
                    "ident": "rrd",
                    "site_id": "stable",
                    "host_name": "stable",
                    "service_name": "Check_MK",
                    "metric_name": "execution_time",
                    "consolidation_func_name": "max",
                    "scale": 1.0,
                },
                "unit": "s",
                "color": "#d080af",
                "visible": True,
            },
        ],
        "additional_html": None,
        "render_options": {},
        "data_range": None,
        "mark_requested_end_time": False,
        "specification": {
            "graph_type": "template",
            "site": "stable",
            "host_name": "stable",
            "service_description": "Check_MK",
            "graph_index": 0,
            "graph_id": "cmk_cpu_time_by_phase",
            "destination": None,
        },
    }
