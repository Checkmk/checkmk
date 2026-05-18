#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title as TitleV1
from cmk.gui.graphing._from_api import RegisteredMetric
from cmk.gui.graphing._graph_metric_expressions import GraphMetricRRDSource
from cmk.gui.graphing._graph_specification import (
    GraphEnvironment,
    GraphMetric,
    GraphRecipe,
    HorizontalRule,
)
from cmk.gui.graphing._graph_templates import (
    _evaluate_graph_plugins,
    resolve_graph_id_from_index,
    sort_registered_graph_plugins,
    TemplateGraphSpecification,
)
from cmk.gui.graphing._legacy import check_metrics
from cmk.gui.graphing._rrd import HostGraphRow, ServiceGraphRow
from cmk.gui.graphing._translated_metrics import (
    compute_translated_metrics,
    parse_perf_data,
    translate_metrics,
)
from cmk.gui.graphing._unit import (
    ConvertibleUnitSpecification,
    DecimalNotation,
)
from cmk.gui.type_defs import Perfdata, PerfDataTuple
from cmk.gui.unit_formatter import AutoPrecision
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils.servicename import ServiceName

_CPU_UTIL_GRAPHS = {
    "cpu_utilization_simple": graphs_v1.Graph(
        name="cpu_utilization_simple",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
        ],
        simple_lines=[
            "util_average",
            "util",
        ],
        optional=["util_average"],
        conflicting=[
            "idle",
            "cpu_util_guest",
            "cpu_util_steal",
            "io_wait",
        ],
    ),
    "util_average_1": graphs_v1.Graph(
        name="util_average_1",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=["util"],
        simple_lines=[
            "util_average",
            metrics_v1.WarningOf("util"),
            metrics_v1.CriticalOf("util"),
        ],
        conflicting=[
            "idle",
            "cpu_util_guest",
            "cpu_util_steal",
            "io_wait",
            "user",
            "system",
        ],
    ),
    "util_average_2": graphs_v1.Graph(
        name="util_average_2",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=["util1"],
        simple_lines=[
            "util15",
            metrics_v1.WarningOf("util1"),
            metrics_v1.CriticalOf("util1"),
        ],
    ),
    "cpu_utilization_3": graphs_v1.Graph(
        name="cpu_utilization_3",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "idle",
            "nice",
        ],
    ),
    "cpu_utilization_4": graphs_v1.Graph(
        name="cpu_utilization_4",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "idle",
            "io_wait",
        ],
    ),
    "cpu_utilization_5": graphs_v1.Graph(
        name="cpu_utilization_5",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
        ],
        simple_lines=[
            "util_average",
            metrics_v1.Sum(
                TitleV1("Total"),
                metrics_v1.Color.GREEN,
                [
                    "user",
                    "system",
                    "io_wait",
                ],
            ),
        ],
        optional=["util_average"],
        conflicting=[
            "util",
            "idle",
            "cpu_util_guest",
            "cpu_util_steal",
        ],
    ),
    "cpu_utilization_5_util": graphs_v1.Graph(
        name="cpu_utilization_5_util",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
        ],
        simple_lines=[
            "util_average",
            "util",
            metrics_v1.WarningOf("util"),
            metrics_v1.CriticalOf("util"),
        ],
        optional=["util_average"],
        conflicting=[
            "cpu_util_guest",
            "cpu_util_steal",
        ],
    ),
    "cpu_utilization_6_steal": graphs_v1.Graph(
        name="cpu_utilization_6_steal",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_steal",
        ],
        simple_lines=[
            "util_average",
            metrics_v1.Sum(
                TitleV1("Total"),
                metrics_v1.Color.GREEN,
                [
                    "user",
                    "system",
                    "io_wait",
                    "cpu_util_steal",
                ],
            ),
        ],
        optional=["util_average"],
        conflicting=[
            "util",
            "cpu_util_guest",
        ],
    ),
    "cpu_utilization_6_steal_util": graphs_v1.Graph(
        name="cpu_utilization_6_steal_util",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_steal",
        ],
        simple_lines=[
            "util_average",
            "util",
            metrics_v1.WarningOf("util"),
            metrics_v1.CriticalOf("util"),
        ],
        optional=["util_average"],
        conflicting=["cpu_util_guest"],
    ),
    "cpu_utilization_6_guest": graphs_v1.Graph(
        name="cpu_utilization_6_guest",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_guest",
        ],
        simple_lines=[
            "util_average",
            metrics_v1.Sum(
                TitleV1("Total"),
                metrics_v1.Color.GREEN,
                [
                    "user",
                    "system",
                    "io_wait",
                    "cpu_util_steal",
                ],
            ),
        ],
        optional=["util_average"],
        conflicting=["util"],
    ),
    "cpu_utilization_6_guest_util": graphs_v1.Graph(
        name="cpu_utilization_6_guest_util",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_guest",
        ],
        simple_lines=[
            "util_average",
            "util",
            metrics_v1.WarningOf("util"),
            metrics_v1.CriticalOf("util"),
        ],
        optional=["util_average"],
        conflicting=["cpu_util_steal"],
    ),
    "cpu_utilization_7": graphs_v1.Graph(
        name="cpu_utilization_7",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_guest",
            "cpu_util_steal",
        ],
        simple_lines=[
            "util_average",
            metrics_v1.Sum(
                TitleV1("Total"),
                metrics_v1.Color.GREEN,
                [
                    "user",
                    "system",
                    "io_wait",
                    "cpu_util_guest",
                    "cpu_util_steal",
                ],
            ),
        ],
        optional=["util_average"],
        conflicting=["util"],
    ),
    "cpu_utilization_7_util": graphs_v1.Graph(
        name="cpu_utilization_7_util",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_guest",
            "cpu_util_steal",
        ],
        simple_lines=[
            "util_average",
            "util",
            metrics_v1.WarningOf("util"),
            metrics_v1.CriticalOf("util"),
        ],
        optional=["util_average"],
    ),
    "cpu_utilization_8": graphs_v1.Graph(
        name="cpu_utilization_8",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "interrupt",
        ],
    ),
    "util_fallback": graphs_v1.Graph(
        name="util_fallback",
        title=TitleV1("CPU utilization"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=["util"],
        simple_lines=[
            metrics_v1.WarningOf("util"),
            metrics_v1.CriticalOf("util"),
        ],
        conflicting=[
            "util_average",
            "system",
            "engine_cpu_util",
        ],
    ),
    "cpu_utilization": graphs_v1.Graph(
        name="cpu_utilization",
        title=TitleV1("CPU utilization"),
        simple_lines=[
            "util",
            "engine_cpu_util",
        ],
    ),
    "cpu_utilization_numcpus": graphs_v1.Graph(
        name="cpu_utilization_numcpus",
        title=TitleV1(
            'CPU utilization (_EXPRESSION:{"metric":"util_numcpu_as_max","scalar":"max"} CPU Threads)'
        ),
        minimal_range=graphs_v1.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "privileged",
        ],
        simple_lines=[
            "util_numcpu_as_max",
            metrics_v1.WarningOf("util_numcpu_as_max"),
            metrics_v1.CriticalOf("util_numcpu_as_max"),
        ],
        optional=[
            "user",
            "privileged",
        ],
    ),
    "cpu_entitlement": graphs_v1.Graph(
        name="cpu_entitlement",
        title=TitleV1("CPU entitlement"),
        compound_lines=["cpu_entitlement"],
        simple_lines=["cpu_entitlement_util"],
    ),
}

_MAIL_GRAPHS = {
    "amount_of_mails_in_queues": graphs_v1.Graph(
        name="amount_of_mails_in_queues",
        title=TitleV1("Amount of mails in queues"),
        compound_lines=[
            "mail_queue_deferred_length",
            "mail_queue_active_length",
        ],
        conflicting=[
            "mail_queue_postfix_total",
            "mail_queue_z1_messenger",
        ],
    ),
    "size_of_mails_in_queues": graphs_v1.Graph(
        name="size_of_mails_in_queues",
        title=TitleV1("Size of mails in queues"),
        compound_lines=[
            "mail_queue_deferred_size",
            "mail_queue_active_size",
        ],
        conflicting=[
            "mail_queue_postfix_total",
            "mail_queue_z1_messenger",
        ],
    ),
    "amount_of_mails_in_secondary_queues": graphs_v1.Graph(
        name="amount_of_mails_in_secondary_queues",
        title=TitleV1("Amount of mails in queues"),
        compound_lines=[
            "mail_queue_hold_length",
            "mail_queue_incoming_length",
            "mail_queue_drop_length",
        ],
        conflicting=[
            "mail_queue_postfix_total",
            "mail_queue_z1_messenger",
        ],
    ),
}

_MEM_GRAPHS = {
    "ram_used": graphs_v1.Graph(
        name="ram_used",
        title=TitleV1("RAM used"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            metrics_v1.MaximumOf(
                "mem_used",
                metrics_v1.Color.GRAY,
            ),
        ),
        compound_lines=["mem_used"],
        simple_lines=[
            metrics_v1.MaximumOf(
                "mem_used",
                metrics_v1.Color.GRAY,
            ),
            metrics_v1.WarningOf("mem_used"),
            metrics_v1.CriticalOf("mem_used"),
        ],
        conflicting=[
            "swap_used",
            "mem_free",
        ],
    ),
    "ram_swap_used": graphs_v1.Graph(
        name="ram_swap_used",
        title=TitleV1("RAM + Swap used"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            metrics_v1.Sum(
                TitleV1(""),
                metrics_v1.Color.GRAY,
                [
                    metrics_v1.MaximumOf(
                        "swap_used",
                        metrics_v1.Color.GRAY,
                    ),
                    metrics_v1.MaximumOf(
                        "mem_used",
                        metrics_v1.Color.GRAY,
                    ),
                ],
            ),
        ),
        compound_lines=[
            "mem_used",
            "swap_used",
        ],
        simple_lines=[
            metrics_v1.Sum(
                TitleV1("Total RAM + Swap installed"),
                metrics_v1.Color.DARK_CYAN,
                [
                    metrics_v1.MaximumOf(
                        "swap_used",
                        metrics_v1.Color.GRAY,
                    ),
                    metrics_v1.MaximumOf(
                        "mem_used",
                        metrics_v1.Color.GRAY,
                    ),
                ],
            ),
            metrics_v1.MaximumOf(
                "mem_used",
                metrics_v1.Color.GRAY,
            ),
        ],
        conflicting=["swap_total"],
    ),
}

_HEAP_MEM_GRAPH = {
    "heap_and_non_heap_memory": graphs_v1.Graph(
        name="heap_and_non_heap_memory",
        title=TitleV1("Heap and non-heap memory"),
        compound_lines=[
            "mem_heap",
            "mem_nonheap",
        ],
        conflicting=[
            "mem_heap_committed",
            "mem_nonheap_committed",
        ],
    ),
    "heap_memory_usage": graphs_v1.Graph(
        name="heap_memory_usage",
        title=TitleV1("Heap memory usage"),
        simple_lines=[
            "mem_heap_committed",
            "mem_heap",
            metrics_v1.WarningOf("mem_heap"),
            metrics_v1.CriticalOf("mem_heap"),
        ],
    ),
    "non-heap_memory_usage": graphs_v1.Graph(
        name="non-heap_memory_usage",
        title=TitleV1("Non-heap memory usage"),
        simple_lines=[
            "mem_nonheap_committed",
            "mem_nonheap",
            metrics_v1.WarningOf("mem_nonheap"),
            metrics_v1.CriticalOf("mem_nonheap"),
            metrics_v1.MaximumOf(
                "mem_nonheap",
                metrics_v1.Color.GRAY,
            ),
        ],
    ),
}


class _FakeTemplateGraphSpecification(TemplateGraphSpecification):
    def fetch_graph_rows(self, env: GraphEnvironment) -> Sequence[HostGraphRow | ServiceGraphRow]:
        perf_data, check_command = parse_perf_data(
            "metric1=163651.992188;;;; metric2=313848.039062;;;", "check_mk-foo", debug=False
        )
        return [
            ServiceGraphRow(
                site_id=SiteId("site_id"),
                host_name=HostName("host_name"),
                service_name=ServiceName("service_name"),
                check_command=check_command,
                translated_metrics=compute_translated_metrics(
                    perf_data,
                    ["metric1", "metric2"],
                    check_command,
                    env.registered_metrics,
                    debug=env.debug,
                    temperature_unit=env.temperature_unit,
                ),
            )
        ]


@pytest.mark.parametrize(
    ("graph_id", "expected"),
    [
        pytest.param(
            None,
            [
                GraphRecipe(
                    title="Graph 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    metrics=[
                        GraphMetric(
                            title="Metric1",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="metric1",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#0080c0",
                        )
                    ],
                ),
                GraphRecipe(
                    title="Graph 2",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    metrics=[
                        GraphMetric(
                            title="Metric2",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="metric2",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#0080c0",
                        )
                    ],
                ),
            ],
            id="no id",
        ),
        pytest.param(
            "graph2",
            [
                GraphRecipe(
                    title="Graph 2",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    metrics=[
                        GraphMetric(
                            title="Metric2",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="metric2",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#0080c0",
                        )
                    ],
                ),
            ],
            id="matching id",
        ),
        pytest.param(
            "wrong",
            [],
            id="non-matching id",
        ),
    ],
)
def test_template_recipes_matching(
    graph_id: str | None,
    expected: Sequence[GraphRecipe],
) -> None:
    graph_specification = _FakeTemplateGraphSpecification(
        site=SiteId("site_id"),
        host_name=HostName("host_name"),
        service_description=ServiceName("service_name"),
        graph_id=graph_id,
    )
    env = GraphEnvironment(
        registered_metrics={
            "metric1": RegisteredMetric(
                name="metric1",
                title_localizer=lambda _localizer: "Metric1",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#0080c0",
            ),
            "metric2": RegisteredMetric(
                name="metric2",
                title_localizer=lambda _localizer: "Metric2",
                unit_spec=ConvertibleUnitSpecification(
                    notation=DecimalNotation(symbol=""),
                    precision=AutoPrecision(digits=2),
                ),
                color="#0080c0",
            ),
        },
        registered_graphs={
            "graph1": graphs_v1.Graph(
                name="graph1",
                title=TitleV1("Graph 1"),
                simple_lines=["metric1"],
            ),
            "graph2": graphs_v1.Graph(
                name="graph2",
                title=TitleV1("Graph 2"),
                simple_lines=["metric2"],
            ),
        },
        user_permissions=UserPermissions({}, {}, {}, []),
        temperature_unit=TemperatureUnit.CELSIUS,
        backend_time_series_fetcher=None,
        debug=False,
    )
    assert [
        r.recipe
        for r in graph_specification.recipes(env, graph_specification.fetch_graph_rows(env))
    ] == expected


def _env_for_resolve_helper(registered_metrics: Mapping[str, RegisteredMetric]) -> GraphEnvironment:
    return GraphEnvironment(
        registered_metrics=registered_metrics,
        registered_graphs={
            "graph1": graphs_v1.Graph(
                name="graph1",
                title=TitleV1("Graph 1"),
                simple_lines=["metric1"],
            ),
            "graph2": graphs_v1.Graph(
                name="graph2",
                title=TitleV1("Graph 2"),
                simple_lines=["metric2"],
            ),
        },
        user_permissions=UserPermissions({}, {}, {}, []),
        temperature_unit=TemperatureUnit.CELSIUS,
        backend_time_series_fetcher=None,
        debug=False,
    )


def _registered_metrics_for_resolve_helper() -> Mapping[str, RegisteredMetric]:
    return {
        "metric1": RegisteredMetric(
            name="metric1",
            title_localizer=lambda _localizer: "Metric1",
            unit_spec=ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol=""),
                precision=AutoPrecision(digits=2),
            ),
            color="#0080c0",
        ),
        "metric2": RegisteredMetric(
            name="metric2",
            title_localizer=lambda _localizer: "Metric2",
            unit_spec=ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol=""),
                precision=AutoPrecision(digits=2),
            ),
            color="#0080c0",
        ),
    }


def _fake_graph_row_fetcher_with_metrics(
    site_id: SiteId | None,
    host_name: HostName,
    service_name: ServiceName,
    registered_metrics: Mapping[str, RegisteredMetric],
    *,
    debug: bool,
    temperature_unit: TemperatureUnit,
) -> ServiceGraphRow:
    perf_data, check_command = parse_perf_data(
        "metric1=163651.992188;;;; metric2=313848.039062;;;", "check_mk-foo", debug=False
    )
    return ServiceGraphRow(
        site_id=SiteId("site_id"),
        host_name=HostName("host_name"),
        service_name=ServiceName("service_name"),
        check_command=check_command,
        translated_metrics=compute_translated_metrics(
            perf_data,
            ["metric1", "metric2"],
            check_command,
            registered_metrics,
            debug=debug,
            temperature_unit=temperature_unit,
        ),
    )


def _fake_graph_row_fetcher_empty(
    site_id: SiteId | None,
    host_name: HostName,
    service_name: ServiceName,
    registered_metrics: Mapping[str, RegisteredMetric],
    *,
    debug: bool,
    temperature_unit: TemperatureUnit,
) -> ServiceGraphRow:
    _perf, check_command = parse_perf_data("", "check_mk-foo", debug=False)
    return ServiceGraphRow(
        site_id=SiteId("site_id"),
        host_name=HostName("host_name"),
        service_name=ServiceName("service_name"),
        check_command=check_command,
        translated_metrics={},
    )


@pytest.mark.parametrize(
    ("graph_index", "expected"),
    [
        pytest.param(0, "graph1", id="first"),
        pytest.param(1, "graph2", id="second"),
        pytest.param(10, None, id="out-of-range"),
        pytest.param(-1, None, id="negative"),
    ],
)
def test_resolve_graph_id_from_index(
    monkeypatch: pytest.MonkeyPatch, graph_index: int, expected: str | None
) -> None:
    monkeypatch.setattr(
        "cmk.gui.graphing._graph_templates.fetch_graph_row",
        _fake_graph_row_fetcher_with_metrics,
    )
    assert (
        resolve_graph_id_from_index(
            env=_env_for_resolve_helper(_registered_metrics_for_resolve_helper()),
            site_id=SiteId("site_id"),
            host_name=HostName("host_name"),
            service_name=ServiceName("service_name"),
            graph_index=graph_index,
        )
        == expected
    )


def test_resolve_graph_id_from_index_no_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.gui.graphing._graph_templates.fetch_graph_row",
        _fake_graph_row_fetcher_empty,
    )
    assert (
        resolve_graph_id_from_index(
            env=_env_for_resolve_helper({}),
            site_id=SiteId("site_id"),
            host_name=HostName("host_name"),
            service_name=ServiceName("service_name"),
            graph_index=0,
        )
        is None
    )


# Synthetic `check_metrics` translations that mirror the production
# perf-data → metric-name mappings the parametrise cases below assume.
# The real production translations come from graphing plug-ins under
# `cmk/plugins/*/graphing/`.
# We register the synthetic equivalents directly into the global registry
# the test target shares with production code so the test covers the full
# `translate_metrics`→ `_evaluate_graph_plugins` integration without
# depending on any specific plug-in being on the runfiles path.
_SYNTHETIC_GRAPH_TEMPLATE_TRANSLATIONS = {
    "check_mk-kernel_util": {
        "wait": {"name": "io_wait"},
        "guest": {"name": "cpu_util_guest"},
        "steal": {"name": "cpu_util_steal"},
    },
    "check_mk-lxc_container_cpu": {
        "wait": {"name": "io_wait"},
    },
    "check_mk-winperf_processor_util": {
        "util": {"name": "util_numcpu_as_max"},
    },
    "check_mk-statgrab_cpu": {
        "guest": {"name": "cpu_util_guest"},
        "steal": {"name": "cpu_util_steal"},
    },
    "check_mk-statgrab_mem": {
        "ramused": {"name": "mem_used"},
        "swapused": {"name": "swap_used"},
        "memused": {"name": "mem_lnx_total_used"},
    },
    "check_mk-lparstat_aix_cpu_util": {
        "wait": {"name": "io_wait"},
    },
    "check_mk-df": {
        "growth": {"name": "fs_growth", "scale": 1024**2 / 86400.0},
    },
}


@pytest.fixture(autouse=True)
def _install_synthetic_translations() -> Iterator[None]:
    """Mutate the shared `check_metrics` dict with the synthetic translations
    needed by `test__evaluate_graph_plugins_*` and `test_template_recipes_fs`,
    then restore the previous state on teardown."""
    saved = {k: check_metrics.get(k) for k in _SYNTHETIC_GRAPH_TEMPLATE_TRANSLATIONS}
    for check_command, translations in _SYNTHETIC_GRAPH_TEMPLATE_TRANSLATIONS.items():
        check_metrics[check_command] = translations  # type: ignore[assignment]
    try:
        yield
    finally:
        for check_command, previous in saved.items():
            if previous is None:
                check_metrics.pop(check_command, None)
            else:
                check_metrics[check_command] = previous


@pytest.mark.parametrize(
    ("metric_names", "check_command", "registered_graphs", "graph_ids"),
    [
        (
            ["user", "system", "wait", "util"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_5_util"],
        ),
        (
            ["util1", "util15"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["util_average_2"],
        ),
        (
            ["util"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["util_fallback"],
        ),
        (
            ["util"],
            "check_mk-lxc_container_cpu",
            _CPU_UTIL_GRAPHS,
            ["util_fallback"],
        ),
        (
            ["wait", "util", "user", "system"],
            "check_mk-lxc_container_cpu",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_5_util"],
        ),
        (
            ["util", "util_average"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["util_average_1"],
        ),
        (
            ["user", "util_numcpu_as_max"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_numcpus"],
        ),
        (
            ["user", "util"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["util_fallback", "METRIC_user"],
        ),
        (
            ["user", "util"],
            "check_mk-winperf_processor_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_numcpus"],
        ),
        (
            ["user", "system", "idle", "nice"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_3"],
        ),
        (
            ["user", "system", "idle", "io_wait"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_4"],
        ),
        (
            ["user", "system", "io_wait"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_5"],
        ),
        (
            ["util_average", "util", "wait", "user", "system", "guest"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_6_guest_util"],
        ),
        (
            ["user", "system", "io_wait", "guest", "steal"],
            "check_mk-statgrab_cpu",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_6_guest", "cpu_utilization_7"],
        ),
        (
            ["user", "system", "interrupt"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_8"],
        ),
        (
            ["user", "system", "wait", "util", "cpu_entitlement", "cpu_entitlement_util"],
            "check_mk-lparstat_aix_cpu_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_entitlement", "cpu_utilization_5_util"],
        ),
        (
            ["ramused", "swapused", "memused"],
            "check_mk-statgrab_mem",
            {},
            ["METRIC_mem_lnx_total_used", "METRIC_mem_used", "METRIC_swap_used"],
        ),
        (
            [
                "aws_ec2_running_ondemand_instances_total",
                "aws_ec2_running_ondemand_instances_t2.micro",
                "aws_ec2_running_ondemand_instances_t2.nano",
            ],
            "check_mk-aws_ec2_limits",
            {
                "aws_ec2_running_ondemand_instances_t2": graphs_v1.Graph(
                    name="aws_ec2_running_ondemand_instances_t2",
                    title=TitleV1("Total running on-demand instances of type t2"),
                    compound_lines=[
                        "aws_ec2_running_ondemand_instances_t2.2xlarge",
                        "aws_ec2_running_ondemand_instances_t2.large",
                        "aws_ec2_running_ondemand_instances_t2.medium",
                        "aws_ec2_running_ondemand_instances_t2.micro",
                        "aws_ec2_running_ondemand_instances_t2.nano",
                        "aws_ec2_running_ondemand_instances_t2.small",
                        "aws_ec2_running_ondemand_instances_t2.xlarge",
                    ],
                    optional=[
                        "aws_ec2_running_ondemand_instances_t2.2xlarge",
                        "aws_ec2_running_ondemand_instances_t2.large",
                        "aws_ec2_running_ondemand_instances_t2.medium",
                        "aws_ec2_running_ondemand_instances_t2.micro",
                        "aws_ec2_running_ondemand_instances_t2.nano",
                        "aws_ec2_running_ondemand_instances_t2.small",
                        "aws_ec2_running_ondemand_instances_t2.xlarge",
                    ],
                ),
                "aws_ec2_running_ondemand_instances": graphs_v1.Graph(
                    name="aws_ec2_running_ondemand_instances",
                    title=TitleV1("Total running on-demand instances"),
                    simple_lines=["aws_ec2_running_ondemand_instances_total"],
                ),
            },
            ["aws_ec2_running_ondemand_instances_t2", "aws_ec2_running_ondemand_instances"],
        ),
    ],
)
def test__evaluate_graph_plugins_1(
    metric_names: Sequence[str],
    check_command: str,
    registered_graphs: Mapping[str, graphs_v1.Graph | graphs_v1.Bidirectional],
    graph_ids: Sequence[str],
    load_plugins: None,
) -> None:
    perfdata: Perfdata = [
        PerfDataTuple(metric_name=n, lookup_metric_name=n, value=0, unit_name="")
        for n in metric_names
    ]
    translated_metrics = translate_metrics(
        perfdata,
        check_command,
        {},
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert sorted(
        [
            graph_id
            for graph_id, _graph_recipe in _evaluate_graph_plugins(
                {},
                sort_registered_graph_plugins(registered_graphs),
                SiteId("site_id"),
                HostName("host_name"),
                ServiceName("service_name"),
                translated_metrics,
                consolidation_function="max",
                temperature_unit=TemperatureUnit.CELSIUS,
            )
        ]
    ) == sorted(graph_ids)


@pytest.mark.parametrize(
    ("metric_names", "warn_crit_min_max", "check_command", "registered_graphs", "graph_ids"),
    [
        pytest.param(
            ["ramused", "swapused", "memused"],
            (0, 1, 2, 3),
            "check_mk-statgrab_mem",
            _MEM_GRAPHS,
            ["METRIC_mem_lnx_total_used", "ram_swap_used"],
            id="ram_swap_used",
        ),
    ],
)
def test__evaluate_graph_plugins_2(
    metric_names: Sequence[str],
    warn_crit_min_max: tuple[int, int, int, int],
    check_command: str,
    registered_graphs: Mapping[str, graphs_v1.Graph | graphs_v1.Bidirectional],
    graph_ids: Sequence[str],
    load_plugins: None,
) -> None:
    perfdata: Perfdata = [
        PerfDataTuple(
            metric_name=n,
            lookup_metric_name=n,
            value=0,
            unit_name="",
            warn=warn_crit_min_max[0],
            crit=warn_crit_min_max[1],
            min_=warn_crit_min_max[2],
            max_=warn_crit_min_max[3],
        )
        for n in metric_names
    ]
    translated_metrics = translate_metrics(
        perfdata,
        check_command,
        {},
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert sorted(
        [
            graph_id
            for graph_id, _graph_recipe in _evaluate_graph_plugins(
                {},
                sort_registered_graph_plugins(registered_graphs),
                SiteId("site_id"),
                HostName("host_name"),
                ServiceName("service_name"),
                translated_metrics,
                consolidation_function="max",
                temperature_unit=TemperatureUnit.CELSIUS,
            )
        ]
    ) == sorted(graph_ids)


@pytest.mark.parametrize(
    (
        "metric_names",
        "predict_metric_names",
        "predict_lower_metric_names",
        "check_command",
        "registered_metrics",
        "registered_graphs",
        "graph_templates",
    ),
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
            {
                "messages_outbound": RegisteredMetric(
                    name="messages_outbound",
                    title_localizer=lambda _localizer: "Outbound messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1e90ff",
                ),
                "messages_inbound": RegisteredMetric(
                    name="messages_inbound",
                    title_localizer=lambda _localizer: "Inbound messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1ee6e6",
                ),
            },
            {
                "inbound_and_outbound_messages": graphs_v1.Graph(
                    name="inbound_and_outbound_messages",
                    title=TitleV1("Inbound and Outbound Messages"),
                    compound_lines=[
                        "messages_outbound",
                        "messages_inbound",
                    ],
                )
            },
            [
                GraphRecipe(
                    title="Inbound and Outbound Messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    metrics=[
                        GraphMetric(
                            title="Outbound messages",
                            line_type="stack",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="messages_outbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#1e90ff",
                        ),
                        GraphMetric(
                            title="Inbound messages",
                            line_type="stack",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="messages_inbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#1ee6e6",
                        ),
                        GraphMetric(
                            title="Prediction of Inbound messages (upper levels)",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_messages_inbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#5a5a5a",
                        ),
                        GraphMetric(
                            title="Prediction of Inbound messages (lower levels)",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_lower_messages_inbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#787878",
                        ),
                        GraphMetric(
                            title="Prediction of Outbound messages (upper levels)",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_messages_outbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#4b4b4b",
                        ),
                        GraphMetric(
                            title="Prediction of Outbound messages (lower levels)",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_lower_messages_outbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#696969",
                        ),
                    ],
                ),
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
            {
                "messages_outbound": RegisteredMetric(
                    name="messages_outbound",
                    title_localizer=lambda _localizer: "Outbound messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1e90ff",
                ),
                "messages_inbound": RegisteredMetric(
                    name="messages_inbound",
                    title_localizer=lambda _localizer: "Inbound messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1ee6e6",
                ),
            },
            {
                "inbound_and_outbound_messages": graphs_v1.Graph(
                    name="inbound_and_outbound_messages",
                    title=TitleV1("Inbound and Outbound Messages"),
                    compound_lines=[
                        "messages_outbound",
                        "messages_inbound",
                    ],
                )
            },
            [
                GraphRecipe(
                    title="Inbound and Outbound Messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    metrics=[
                        GraphMetric(
                            title="Outbound messages",
                            line_type="stack",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="messages_outbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#1e90ff",
                        ),
                        GraphMetric(
                            title="Inbound messages",
                            line_type="stack",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="messages_inbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#1ee6e6",
                        ),
                    ],
                ),
                GraphRecipe(
                    title="Foo",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    metrics=[
                        GraphMetric(
                            title="Foo",
                            line_type="area",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="foo",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                type="convertible",
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#cc00ff",
                        )
                    ],
                ),
                GraphRecipe(
                    title="Prediction of Foo (upper levels)",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[
                        HorizontalRule(
                            value=2.0, rendered_value="2", color="#ff3232", title="Critical"
                        ),
                        HorizontalRule(
                            value=1.0, rendered_value="1", color="#ffd000", title="Warning"
                        ),
                    ],
                    omit_zero_metrics=False,
                    metrics=[
                        GraphMetric(
                            title="Prediction of Foo (upper levels)",
                            line_type="area",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_foo",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#4b4b4b",
                        )
                    ],
                ),
                GraphRecipe(
                    title="Prediction of Foo (lower levels)",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[
                        HorizontalRule(
                            value=4.0, rendered_value="4", color="#ff3232", title="Critical"
                        ),
                        HorizontalRule(
                            value=3.0, rendered_value="3", color="#ffd000", title="Warning"
                        ),
                    ],
                    omit_zero_metrics=False,
                    metrics=[
                        GraphMetric(
                            title="Prediction of Foo (lower levels)",
                            line_type="area",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_lower_foo",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#5a5a5a",
                        )
                    ],
                ),
            ],
            id="does-not-match",
        ),
    ],
)
def test__evaluate_graph_plugins_with_predictive_metrics(
    metric_names: Sequence[str],
    predict_metric_names: Sequence[str],
    predict_lower_metric_names: Sequence[str],
    check_command: str,
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_v1.Graph | graphs_v1.Bidirectional],
    graph_templates: Sequence[GraphRecipe],
) -> None:
    perfdata: Perfdata = (
        [
            PerfDataTuple(metric_name=n, lookup_metric_name=n, value=0, unit_name="")
            for n in metric_names
        ]
        + [
            PerfDataTuple(
                metric_name=n,
                lookup_metric_name=n[8:],
                value=0,
                unit_name="",
                warn=1,
                crit=2,
            )
            for n in predict_metric_names
        ]
        + [
            PerfDataTuple(
                metric_name=n,
                lookup_metric_name=n[14:],
                value=0,
                unit_name="",
                warn=3,
                crit=4,
            )
            for n in predict_lower_metric_names
        ]
    )
    translated_metrics = translate_metrics(
        perfdata,
        check_command,
        registered_metrics,
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert [
        recipe
        for _graph_id, recipe in _evaluate_graph_plugins(
            registered_metrics,
            sort_registered_graph_plugins(registered_graphs),
            SiteId("site_id"),
            HostName("host_name"),
            ServiceName("service_name"),
            translated_metrics,
            consolidation_function="max",
            temperature_unit=TemperatureUnit.CELSIUS,
        )
    ] == graph_templates


@pytest.mark.parametrize(
    ("metric_names", "registered_graphs", "graph_ids"),
    [
        pytest.param(
            ["user_time", "children_user_time", "system_time", "children_system_time"],
            {
                "used_cpu_time": graphs_v1.Graph(
                    name="used_cpu_time",
                    title=TitleV1("Used CPU Time"),
                    compound_lines=[
                        "user_time",
                        "children_user_time",
                        "system_time",
                        "children_system_time",
                    ],
                    simple_lines=[
                        metrics_v1.Sum(
                            TitleV1("Total"),
                            metrics_v1.Color.DARK_BLUE,
                            [
                                "user_time",
                                "children_user_time",
                                "system_time",
                                "children_system_time",
                            ],
                        )
                    ],
                    conflicting=[
                        "cmk_time_agent",
                        "cmk_time_snmp",
                        "cmk_time_ds",
                    ],
                )
            },
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
            {
                "used_cpu_time": graphs_v1.Graph(
                    name="used_cpu_time",
                    title=TitleV1("Used CPU Time"),
                    compound_lines=[
                        "user_time",
                        "children_user_time",
                        "system_time",
                        "children_system_time",
                    ],
                    simple_lines=[
                        metrics_v1.Sum(
                            TitleV1("Total"),
                            metrics_v1.Color.DARK_BLUE,
                            [
                                "user_time",
                                "children_user_time",
                                "system_time",
                                "children_system_time",
                            ],
                        )
                    ],
                    conflicting=[
                        "cmk_time_agent",
                        "cmk_time_snmp",
                        "cmk_time_ds",
                    ],
                )
            },
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
            {
                "cpu_time": graphs_v1.Graph(
                    name="cpu_time",
                    title=TitleV1("CPU Time"),
                    compound_lines=[
                        "user_time",
                        "system_time",
                    ],
                    simple_lines=[
                        metrics_v1.Sum(
                            TitleV1("Total"),
                            metrics_v1.Color.GRAY,
                            [
                                "user_time",
                                "system_time",
                            ],
                        )
                    ],
                    conflicting=["children_user_time"],
                )
            },
            ["cpu_time"],
            id="cpu_time",
        ),
        pytest.param(
            ["user_time", "system_time", "children_user_time"],
            {
                "cpu_time": graphs_v1.Graph(
                    name="cpu_time",
                    title=TitleV1("CPU Time"),
                    compound_lines=[
                        "user_time",
                        "system_time",
                    ],
                    simple_lines=[
                        metrics_v1.Sum(
                            TitleV1("Total"),
                            metrics_v1.Color.GRAY,
                            [
                                "user_time",
                                "system_time",
                            ],
                        )
                    ],
                    conflicting=["children_user_time"],
                )
            },
            ["METRIC_children_user_time", "METRIC_system_time", "METRIC_user_time"],
            id="cpu_time_conflicting_metrics",
        ),
        pytest.param(
            ["util", "util_average"],
            _CPU_UTIL_GRAPHS,
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
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_4", "cpu_utilization_7_util", "METRIC_util_average_1"],
            id="util_average_1_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "util_average", "util"],
            _CPU_UTIL_GRAPHS,
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
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_4", "cpu_utilization_7_util"],
            id="cpu_utilization_simple_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "util_average"],
            _CPU_UTIL_GRAPHS,
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
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_4", "cpu_utilization_7_util"],
            id="cpu_utilization_5_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "util_average", "util"],
            _CPU_UTIL_GRAPHS,
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
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_5_util_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_steal", "util_average"],
            _CPU_UTIL_GRAPHS,
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
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_steal_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_steal", "util_average", "util"],
            _CPU_UTIL_GRAPHS,
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
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_steal_util_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "util_average", "cpu_util_steal"],
            _CPU_UTIL_GRAPHS,
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
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_guest_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "util_average", "util"],
            _CPU_UTIL_GRAPHS,
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
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_guest_util_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "cpu_util_steal", "util_average"],
            _CPU_UTIL_GRAPHS,
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
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_7_conflicting_metrics",
        ),
        pytest.param(
            ["util"],
            _CPU_UTIL_GRAPHS,
            ["util_fallback"],
            id="util_fallback",
        ),
        pytest.param(
            ["util", "util_average", "system", "engine_cpu_util"],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization", "METRIC_system", "METRIC_util_average"],
            id="util_fallback_conflicting_metrics",
        ),
        pytest.param(
            ["fs_used", "fs_free", "fs_size"],
            {
                "fs_used": graphs_v1.Graph(
                    name="fs_used",
                    title=TitleV1("Size and used space"),
                    minimal_range=graphs_v1.MinimalRange(
                        0,
                        metrics_v1.MaximumOf(
                            "fs_used",
                            metrics_v1.Color.GRAY,
                        ),
                    ),
                    compound_lines=[
                        "fs_used",
                        "fs_free",
                    ],
                    simple_lines=[
                        "fs_size",
                        metrics_v1.WarningOf("fs_used"),
                        metrics_v1.CriticalOf("fs_used"),
                    ],
                    conflicting=["reserved"],
                )
            },
            ["fs_used"],
            id="fs_used",
        ),
        pytest.param(
            ["fs_used", "fs_size", "reserved"],
            {
                "fs_used": graphs_v1.Graph(
                    name="fs_used",
                    title=TitleV1("Size and used space"),
                    minimal_range=graphs_v1.MinimalRange(
                        0,
                        metrics_v1.MaximumOf(
                            "fs_used",
                            metrics_v1.Color.GRAY,
                        ),
                    ),
                    compound_lines=[
                        "fs_used",
                        "fs_free",
                    ],
                    simple_lines=[
                        "fs_size",
                        metrics_v1.WarningOf("fs_used"),
                        metrics_v1.CriticalOf("fs_used"),
                    ],
                    conflicting=["reserved"],
                )
            },
            ["METRIC_fs_size", "METRIC_fs_used", "METRIC_reserved"],
            id="fs_used_conflicting_metrics",
        ),
        pytest.param(
            ["mail_queue_deferred_length", "mail_queue_active_length"],
            _MAIL_GRAPHS,
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
            _MAIL_GRAPHS,
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
            _MAIL_GRAPHS,
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
            _MAIL_GRAPHS,
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
            _MAIL_GRAPHS,
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
            _MAIL_GRAPHS,
            [
                "METRIC_mail_queue_drop_length",
                "METRIC_mail_queue_hold_length",
                "METRIC_mail_queue_incoming_length",
                "METRIC_mail_queue_postfix_total",
                "METRIC_mail_queue_z1_messenger",
            ],
            id="amount_of_mails_in_secondary_queues_conflicting_metrics",
        ),
        pytest.param(
            ["mem_used", "swap_used"],
            _MEM_GRAPHS,
            ["ram_swap_used"],
            id="ram_used_conflicting_metrics",
        ),
        pytest.param(
            ["mem_used", "swap_used", "swap_total"],
            _MEM_GRAPHS,
            ["METRIC_mem_used", "METRIC_swap_total", "METRIC_swap_used"],
            id="ram_swap_used_conflicting_metrics",
        ),
        pytest.param(
            ["mem_lnx_active", "mem_lnx_inactive"],
            {
                "active_and_inactive_memory": graphs_v1.Graph(
                    name="active_and_inactive_memory",
                    title=TitleV1("Active and inactive memory"),
                    compound_lines=[
                        "mem_lnx_active",
                        "mem_lnx_inactive",
                    ],
                )
            },
            ["active_and_inactive_memory"],
            id="active_and_inactive_memory",
        ),
        pytest.param(
            ["mem_used"],
            _MEM_GRAPHS,
            ["ram_used"],
            id="ram_used",
        ),
        pytest.param(
            ["mem_heap", "mem_nonheap"],
            _HEAP_MEM_GRAPH,
            ["heap_and_non_heap_memory"],
            id="heap_and_non_heap_memory",
        ),
        pytest.param(
            ["mem_heap", "mem_nonheap", "mem_heap_committed", "mem_nonheap_committed"],
            _HEAP_MEM_GRAPH,
            ["heap_memory_usage", "non-heap_memory_usage"],
            id="heap_and_non_heap_memory_conflicting_metrics",
        ),
    ],
)
def test_conflicting_metrics(
    metric_names: Sequence[str],
    registered_graphs: Mapping[str, graphs_v1.Graph | graphs_v1.Bidirectional],
    graph_ids: Sequence[str],
) -> None:
    # Hard to find all avail metric names of a check plug-in.
    # We test conflicting metrics as following:
    # 1. write test for expected metric names of a graph template if it has "conflicting_metrics"
    # 2. use metric names from (1) and conflicting metrics
    perfdata: Perfdata = [
        PerfDataTuple(metric_name=n, lookup_metric_name=n, value=0, unit_name="")
        for n in metric_names
    ]
    translated_metrics = translate_metrics(
        perfdata,
        "check_command",
        {},
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert sorted(
        [
            graph_id
            for graph_id, _graph_recipe in _evaluate_graph_plugins(
                {},
                sort_registered_graph_plugins(registered_graphs),
                SiteId("site_id"),
                HostName("host_name"),
                ServiceName("service_name"),
                translated_metrics,
                consolidation_function="max",
                temperature_unit=TemperatureUnit.CELSIUS,
            )
        ]
    ) == sorted(graph_ids)
