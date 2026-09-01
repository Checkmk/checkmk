#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostAddress
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title
from cmk.graphing_engine import HostName as EngineHostName
from cmk.graphing_engine import MetricName as EngineMetricName
from cmk.graphing_engine import Service
from cmk.graphing_engine import ServiceName as EngineServiceName
from cmk.gui.graphing._engine_dispatch import legacy_graph_id
from cmk.gui.graphing._engine_plugins import registered_graphs as engine_registered_graphs
from cmk.gui.graphing._engine_template_graphs import build_template_graphs
from cmk.gui.graphing._from_api import graphs_from_api
from cmk.gui.graphing._graph_templates import (
    sort_registered_graph_plugins,
    TemplateGraphSpecification,
)

_HOST = "host_name"
_SERVICE = "service_name"


def _metric(name: str) -> metrics_v1.Metric:
    return metrics_v1.Metric(
        name=name,
        title=Title("Metric"),
        unit=metrics_v1.Unit(metrics_v1.DecimalNotation("")),
        color=metrics_v1.Color.BLUE,
    )


class _FetchMetricNames:
    def __init__(self, metric_names: Sequence[str]) -> None:
        self._metric_names = metric_names

    def __call__(self) -> Mapping[Service, frozenset[EngineMetricName]]:
        return {
            Service(
                host_name=EngineHostName(_HOST), service_name=EngineServiceName(_SERVICE)
            ): frozenset(EngineMetricName(name) for name in self._metric_names)
        }


def _engine_ids(
    metric_names: Sequence[str],
    registered_graphs: Mapping[str, graphs_v1.Graph | graphs_v1.Bidirectional],
    registered_metrics: Mapping[str, metrics_v1.Metric],
) -> list[str]:
    ordered = [plugin for _name, plugin in sort_registered_graph_plugins(registered_graphs)]
    built = build_template_graphs(
        TemplateGraphSpecification(
            site=None, host_name=HostAddress(_HOST), service_description=_SERVICE
        ),
        registered_graphs=ordered,
        registered_metrics=registered_metrics,
        fetch_metric_names=_FetchMetricNames(metric_names),
    )
    return [legacy_graph_id(b.graph, ordered) for b in built]


@pytest.mark.parametrize(
    "metric_names,registered_graphs,expected",
    [
        pytest.param(
            ["cpu_user", "cpu_system"],
            {},
            ["METRIC_cpu_system", "METRIC_cpu_user"],
            id="fallbacks-are-alphabetical",
        ),
        pytest.param(
            ["util", "if_in", "extra", "cpu_user", "if_out"],
            {},
            [
                "METRIC_cpu_user",
                "METRIC_extra",
                "METRIC_if_in",
                "METRIC_if_out",
                "METRIC_util",
            ],
            id="fallbacks-are-alphabetical-not-insertion-ordered",
        ),
        pytest.param(
            ["cpu_user", "cpu_system"],
            {
                "cpu": graphs_v1.Graph(
                    name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
                )
            },
            ["cpu"],
            id="a-plugin-claims-its-metrics",
        ),
        pytest.param(
            ["cpu_user", "cpu_system", "extra", "util"],
            {
                "cpu": graphs_v1.Graph(
                    name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
                )
            },
            ["cpu", "METRIC_extra", "METRIC_util"],
            id="plugins-come-before-fallbacks",
        ),
        pytest.param(
            ["cpu_user", "extra"],
            {
                "b_graph": graphs_v1.Graph(
                    name="b_graph", title=Title("B"), simple_lines=["cpu_user"]
                ),
                "a_graph": graphs_v1.Graph(
                    name="a_graph", title=Title("A"), simple_lines=["extra"]
                ),
            },
            ["b_graph", "a_graph"],
            id="plugins-keep-their-registration-order",
        ),
    ],
)
def test_the_engine_discovers_a_services_graphs_in_a_pinned_order(
    metric_names: Sequence[str],
    registered_graphs: Mapping[str, graphs_v1.Graph | graphs_v1.Bidirectional],
    expected: Sequence[str],
    request_context: None,
    load_plugins: None,
) -> None:
    registered_metrics = {name: _metric(name) for name in metric_names}

    assert _engine_ids(metric_names, registered_graphs, registered_metrics) == expected


def test_the_engine_registered_graphs_keep_the_legacy_plugin_order(load_plugins: None) -> None:
    assert [plugin.name for plugin in engine_registered_graphs()] == [
        name for name, _plugin in sort_registered_graph_plugins(graphs_from_api)
    ]
