#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.gui.config import Config
from cmk.gui.dashboard.dashlet.dashlets.graph import _graph_templates_autocompleter_testable
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


def test_graph_templates_autocompleter_testable_unconstrained() -> None:
    assert _graph_templates_autocompleter_testable(
        config=Config(),
        value_entered_by_user="",
        params={"show_independent_of_context": True},
        registered_metrics={},
        registered_graphs={
            "graph1": Graph(
                name="graph1",
                title=Title("Graph 1"),
                simple_lines=["metric1"],
            )
        },
    ) == [
        (
            "graph1",
            "Graph 1",
        ),
    ]


@pytest.mark.usefixtures("request_context")
def test_graph_templates_autocompleter_testable_constrained_by_host_and_service(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=True):
        mock_livestatus.add_table(
            "services",
            [
                {
                    "host_name": "my-host",
                    "service_description": "my-service",
                    "service_check_command": "check_command",
                    "service_perf_data": "metric1=1.35;;;; metric2=2.89;;;;",
                    "service_metrics": ["metric1", "metric2"],
                }
            ],
        )
        mock_livestatus.expect_query(
            """GET services
Columns: service_check_command service_perf_data service_metrics
Filter: host_name = my-host
Filter: service_description = my-service

"""
        )

        assert _graph_templates_autocompleter_testable(
            config=Config(),
            value_entered_by_user="",
            params={"context": {"host": {"host": "my-host"}, "service": {"service": "my-service"}}},
            registered_metrics={},
            registered_graphs={
                "graph1": Graph(
                    name="graph1",
                    title=Title("Graph 1"),
                    simple_lines=["metric1"],
                )
            },
        ) == [
            (
                "graph1",
                "Graph 1",
            ),
            (
                "METRIC_metric2",
                "Metric: Metric2",
            ),
        ]


@pytest.mark.usefixtures("request_context")
def test_graph_templates_autocompleter_testable_constrained_by_host_and_service_and_user_input(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=True):
        mock_livestatus.add_table(
            "services",
            [
                {
                    "host_name": "my-host",
                    "service_description": "my-service",
                    "service_check_command": "check_command",
                    "service_perf_data": "metric1=1.35;;;; metric2=2.89;;;;",
                    "service_metrics": ["metric1", "metric2"],
                }
            ],
        )
        mock_livestatus.expect_query(
            """GET services
Columns: service_check_command service_perf_data service_metrics
Filter: host_name = my-host
Filter: service_description = my-service

"""
        )

        assert _graph_templates_autocompleter_testable(
            config=Config(),
            value_entered_by_user="1",
            params={"context": {"host": {"host": "my-host"}, "service": {"service": "my-service"}}},
            registered_metrics={},
            registered_graphs={
                "graph1": Graph(
                    name="graph1",
                    title=Title("Graph 1"),
                    simple_lines=["metric1"],
                )
            },
        ) == [
            (
                "graph1",
                "Graph 1",
            ),
        ]
