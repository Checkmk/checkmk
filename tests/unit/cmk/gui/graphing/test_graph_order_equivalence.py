#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The engine must discover a service's graphs in the order the legacy path did.

resolve_graph_id_from_index() maps a stored positional graph index - written by
pre-CMK-7308 dashlet and report configs - onto a stable graph id. Moving it onto the
engine is only safe while both paths agree on the sequence, not merely the set: a
divergence silently resolves a stored index to a different graph.

These tests are the licence for that move, and they go with the legacy path.
"""

from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId
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
from cmk.gui.graphing._from_api import graphs_from_api, parse_metric_from_api
from cmk.gui.graphing._graph_templates import (
    _evaluate_graph_plugins,
    sort_registered_graph_plugins,
    TemplateGraphSpecification,
)
from cmk.gui.graphing._translated_metrics import translate_metrics
from cmk.gui.type_defs import PerfDataTuple
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils.servicename import ServiceName

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


def _legacy_ids(
    metric_names: Sequence[str],
    registered_graphs: Mapping[str, graphs_v1.Graph | graphs_v1.Bidirectional],
    api_metrics: Mapping[str, metrics_v1.Metric],
) -> list[str]:
    # The legacy path reads the GUI's parsed metrics, the engine the plug-in API ones.
    registered_metrics = {
        name: parse_metric_from_api(metric) for name, metric in api_metrics.items()
    }
    translated = translate_metrics(
        [
            PerfDataTuple(metric_name=n, lookup_metric_name=n, value=0, unit_name="")
            for n in metric_names
        ],
        "check_command",
        registered_metrics,
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    return [
        graph_id
        for graph_id, _recipe in _evaluate_graph_plugins(
            registered_metrics,
            sort_registered_graph_plugins(registered_graphs),
            SiteId("site_id"),
            HostName(_HOST),
            ServiceName(_SERVICE),
            translated,
            consolidation_function="max",
            temperature_unit=TemperatureUnit.CELSIUS,
        )
    ]


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
    "metric_names,registered_graphs",
    [
        pytest.param(["cpu_user", "cpu_system"], {}, id="fallbacks-only-two"),
        pytest.param(
            ["util", "if_in", "extra", "cpu_user", "if_out"], {}, id="fallbacks-only-five"
        ),
        pytest.param(
            ["cpu_user", "cpu_system"],
            {
                "cpu": graphs_v1.Graph(
                    name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
                )
            },
            id="one-plugin-claims-both",
        ),
        pytest.param(
            ["cpu_user", "cpu_system", "extra", "util"],
            {
                "cpu": graphs_v1.Graph(
                    name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
                )
            },
            id="plugin-then-fallbacks",
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
            id="two-plugins-registration-order",
        ),
    ],
)
def test_the_engine_discovers_a_services_graphs_in_the_legacy_order(
    metric_names: Sequence[str],
    registered_graphs: Mapping[str, graphs_v1.Graph | graphs_v1.Bidirectional],
    request_context: None,
    load_plugins: None,
) -> None:
    registered_metrics = {name: _metric(name) for name in metric_names}

    assert _engine_ids(metric_names, registered_graphs, registered_metrics) == _legacy_ids(
        metric_names, registered_graphs, registered_metrics
    )


def test_the_engine_registered_graphs_keep_the_legacy_plugin_order(load_plugins: None) -> None:
    # resolve_graph_id_from_index() indexes into this sequence, so the engine's own plug-in
    # source has to hand them over in sort_registered_graph_plugins() order too.
    assert [plugin.name for plugin in engine_registered_graphs()] == [
        name for name, _plugin in sort_registered_graph_plugins(graphs_from_api)
    ]
